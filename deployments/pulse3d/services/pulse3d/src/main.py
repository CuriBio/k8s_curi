import json
import os
import tempfile
import time
import uuid
from collections import defaultdict
from datetime import datetime

import boto3
import pandas as pd
import structlog
from auth import ScopeTags, Scopes, ProtectedAny, check_prohibited_product, ProhibitedProductError
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from jobs import (
    check_customer_quota,
    create_analysis_preset,
    create_job,
    create_upload,
    delete_jobs,
    delete_uploads,
    get_jobs,
    get_uploads,
)
from pulse3D.constants import (
    AMPLITUDE_UUID,
    CALCULATED_METRIC_DISPLAY_NAMES,
    DATA_TYPE_TO_AMPLITUDE_LABEL,
    DATA_TYPE_TO_UNIT_LABEL,
    DEFAULT_AMPLITUDE_LABEL,
    DEFAULT_BASELINE_WIDTHS,
    DEFAULT_NB_WIDTH_FACTORS,
    DEFAULT_PROMINENCE_FACTORS,
    DEFAULT_UNIT_LABEL,
    DEFAULT_WIDTH_FACTORS,
)
from semver import VersionInfo
from stream_zip import ZIP_64, stream_zip
from starlette_context import context, request_cycle_context
from structlog.contextvars import bind_contextvars, clear_contextvars
from utils.db import AsyncpgPoolDep
from utils.logging import setup_logger, bind_context_to_logger
from utils.s3 import S3Error, generate_presigned_post, generate_presigned_url, upload_file_to_s3
from uvicorn.protocols.utils import get_path_with_query_string

from core.config import DASHBOARD_URL, DATABASE_URL, MANTARRAY_LOGS_BUCKET, PULSE3D_UPLOADS_BUCKET
from models.models import (
    GenericErrorResponse,
    JobDownloadRequest,
    JobRequest,
    JobResponse,
    SavePresetRequest,
    UploadDownloadRequest,
    UploadRequest,
    UploadResponse,
    UsageQuota,
    WaveformDataResponse,
)
from models.types import TupleParam

setup_logger()
logger = structlog.stdlib.get_logger("api.access")

app = FastAPI(openapi_url=None)
asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[DASHBOARD_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next) -> Response:
    request.state.pgpool = await asyncpg_pool()
    # clear previous request variables
    clear_contextvars()
    # get request details for logging
    if (client_ip := request.headers.get("X-Forwarded-For")) is None:
        client_ip = f"{request.client.host}:{request.client.port}"

    url = get_path_with_query_string(request.scope)
    http_method = request.method
    http_version = request.scope["http_version"]
    start_time = time.perf_counter_ns()

    # bind details to logger
    bind_contextvars(url=str(request.url), method=http_method, client_ip=client_ip)

    with request_cycle_context({}):
        response = await call_next(request)

        process_time = time.perf_counter_ns() - start_time
        status_code = response.status_code

        logger.info(
            f"""{client_ip} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
            status_code=status_code,
            duration=process_time / 10**9,
            **context,
        )

    return response


@app.on_event("startup")
async def startup():
    await asyncpg_pool()


# TODO define response model
@app.get("/uploads")
async def get_info_of_uploads(
    request: Request,
    upload_ids: list[uuid.UUID] | None = Query(None),
    token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ)),
):
    # need to convert to UUIDs to str to avoid issues with DB
    if upload_ids:
        upload_ids = [str(upload_id) for upload_id in upload_ids]

    try:
        account_id = str(uuid.UUID(token.account_id))
        account_type = token.account_type
        is_user = account_type == "user"

        bind_context_to_logger(
            {"user_id": token.userid, "customer_id": token.customer_id, "upload_ids": upload_ids}
        )

        # give advanced privileges to access all uploads under customer_id
        # TODO update this to product specific when landing page is specced out more
        if Scopes.MANTARRAY__RW_ALL_DATA in token.scopes:
            account_id = str(uuid.UUID(token.customer_id))
            # catches in the else block like customers in get_uploads, just set here so it's not customer and become confusing
            account_type = "rw_all_user"

        async with request.state.pgpool.acquire() as con:
            uploads = await get_uploads(
                con=con, account_type=account_type, account_id=account_id, upload_ids=upload_ids
            )
            if is_user:
                # customer accounts don't matter here because they don't have the ability to delete
                for upload in uploads:
                    # need way on FE to tell if user owns recordings besides username since current user's username is not stored on the FE. We want to prevent users from attempting to delete files that aren't theirs before calling /delete route
                    upload["owner"] = str(upload["user_id"]) == account_id

            return uploads

    except Exception:
        logger.exception("Failed to get uploads")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/uploads", response_model=UploadResponse | GenericErrorResponse)
async def create_recording_upload(
    request: Request, details: UploadRequest, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE))
):
    try:
        user_id = str(uuid.UUID(token.userid))
        customer_id = str(uuid.UUID(token.customer_id))
        # generating uuid here instead of letting PG handle it so that it can be inserted into the prefix more easily
        upload_id = uuid.uuid4()
        s3_key = f"uploads/{customer_id}/{user_id}/{upload_id}"

        # TODO Luci (09/30/2023) can remove after MA v1.2.2+, will no longer need to handle pulse3d upload types
        upload_type = details.upload_type if details.upload_type != "pulse3d" else "mantarray"
        check_prohibited_product(token.scopes, upload_type)

        bind_context_to_logger(
            {
                "user_id": user_id,
                "customer_id": customer_id,
                "upload_id": str(upload_id),
                "upload_type": upload_type,
            }
        )

        upload_params = {
            "prefix": s3_key,
            "filename": details.filename,
            "md5": details.md5s,
            "user_id": user_id,
            "type": upload_type,
            "customer_id": customer_id,
            "auto_upload": details.auto_upload,
            "upload_id": upload_id,
        }

        async with request.state.pgpool.acquire() as con:
            usage_quota = await check_customer_quota(con, customer_id, upload_type)
            if usage_quota["uploads_reached"]:
                return GenericErrorResponse(message=usage_quota, error="UsageError")

            # Tanner (7/5/22): using a transaction here so that if _generate_presigned_post fails
            # then the new upload row won't be committed
            async with con.transaction():
                upload_id = await create_upload(con=con, upload_params=upload_params)
                params = _generate_presigned_post(details, PULSE3D_UPLOADS_BUCKET, s3_key)
                return UploadResponse(id=upload_id, params=params)
    except ProhibitedProductError:
        logger.exception(f"User does not permission to upload {upload_type} recordings")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    except S3Error:
        logger.exception("Error creating recording")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    except Exception:
        logger.exception("Error creating recording")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.delete("/uploads")
async def soft_delete_uploads(
    request: Request,
    upload_ids: list[uuid.UUID] = Query(None),
    token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ)),
):
    # make sure at least one upload ID was given
    if not upload_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No upload IDs given")
    # need to convert UUIDs to str to avoid issues with DB
    upload_ids = [str(upload_id) for upload_id in upload_ids]

    try:
        account_id = str(uuid.UUID(token.account_id))

        bind_context_to_logger(
            {"user_id": token.userid, "customer_id": token.customer_id, "upload_ids": upload_ids}
        )

        async with request.state.pgpool.acquire() as con:
            await delete_uploads(
                con=con, account_type=token.account_type, account_id=account_id, upload_ids=upload_ids
            )
    except Exception:
        logger.exception("Error deleting upload")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/uploads/download")
async def download_zip_files(
    request: Request, details: UploadDownloadRequest, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ))
):
    upload_ids = details.upload_ids

    # make sure at least one job ID was given
    if not upload_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No upload IDs given")

    # need to convert UUIDs to str to avoid issues with DB
    upload_ids = [str(id) for id in upload_ids]
    account_id = str(uuid.UUID(token.account_id))
    account_type = token.account_type

    bind_context_to_logger(
        {"user_id": token.userid, "customer_id": token.customer_id, "upload_ids": upload_ids}
    )

    # give advanced privileges to access all uploads under customer_id
    if Scopes.MANTARRAY__RW_ALL_DATA in token.scopes:
        account_id = str(uuid.UUID(token.customer_id))
        account_type = "rw_all_user"

    try:
        async with request.state.pgpool.acquire() as con:
            uploads = await get_uploads(
                con=con, account_type=account_type, account_id=account_id, upload_ids=upload_ids
            )

        # get filenames and s3 keys to download
        keys = [f"{upload['prefix']}/{upload['filename']}" for upload in uploads]
        filenames = [upload["filename"] for upload in uploads]

        if len(upload_ids) == 1:
            # if only one file requested, return single presigned URL
            return {"filename": filenames[0], "url": generate_presigned_url(PULSE3D_UPLOADS_BUCKET, keys[0])}
        else:
            # Grab ZIP file from in-memory, make response with correct MIME-type
            return StreamingResponse(
                content=stream_zip(
                    _yield_s3_objects(bucket=PULSE3D_UPLOADS_BUCKET, keys=keys, filenames=filenames)
                ),
                media_type="application/zip",
            )

    except Exception:
        logger.exception("Failed to download recording files")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# TODO Tanner (4/21/22): probably want to move this to a more general svc (maybe in apiv2-dep) dedicated to uploading misc files to s3
@app.post("/logs")
async def create_log_upload(
    request: Request, details: UploadRequest, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE))
):
    try:
        user_id = str(uuid.UUID(token.userid))
        customer_id = str(uuid.UUID(token.customer_id))
        s3_key = f"{customer_id}/{user_id}"

        bind_context_to_logger({"customer_id": customer_id, "user_id": user_id})

        params = _generate_presigned_post(details, MANTARRAY_LOGS_BUCKET, s3_key)
        return UploadResponse(params=params)
    except S3Error:
        logger.exception("Error creating log upload")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    except Exception:
        logger.exception("Error creating log upload")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _generate_presigned_post(details, bucket, s3_key):
    s3_key += f"/{details.filename}"
    logger.info(f"Generating presigned upload url for {bucket}/{s3_key}")
    params = generate_presigned_post(bucket=bucket, key=s3_key, md5s=details.md5s)
    return params


# TODO create response model
@app.get("/jobs")
async def get_info_of_jobs(
    request: Request,
    job_ids: list[uuid.UUID] | None = Query(None),
    download: bool = Query(True),
    token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ)),
):
    # need to convert UUIDs to str to avoid issues with DB
    if job_ids:
        job_ids = [str(job_id) for job_id in job_ids]

    try:
        account_id = str(uuid.UUID(token.account_id))
        account_type = token.account_type
        is_user = account_type == "user"

        bind_context_to_logger(
            {"user_id": token.userid, "customer_id": token.customer_id, "job_ids": job_ids}
        )

        async with request.state.pgpool.acquire() as con:
            jobs = await _get_jobs(con, token, job_ids)

        response = {"jobs": []}
        for job in jobs:
            obj_key = job["object_key"]
            job_info = {
                "id": job["job_id"],
                "status": job["status"],
                "upload_id": job["upload_id"],
                "object_key": obj_key,
                "created_at": job["created_at"],
                "meta": job["job_meta"],
            }

            if is_user:
                # customer accounts don't have the ability to delete so doesn't need this key:value
                # need way on FE to tell if user owns recordings besides username since current user's username is not stored on the FE. We want to prevent users from attempting to delete files that aren't theirs before calling /delete route
                job_info["owner"] = str(job["user_id"]) == account_id

            if job_info["status"] == "finished" and download:
                # This is in case any current users uploaded files before object_key was dropped from uploads table and added to jobs_result
                if obj_key:
                    logger.info(f"Generating presigned download url for {obj_key}")
                    try:
                        job_info["url"] = generate_presigned_url(PULSE3D_UPLOADS_BUCKET, obj_key)
                    except Exception:
                        logger.exception(f"Error generating presigned url for {obj_key}")
                        job_info["url"] = "Error creating download link"
                else:
                    job_info["url"] = None

            elif job_info["status"] == "error":
                try:
                    job_info["error_info"] = json.loads(job["job_meta"])["error"]
                except KeyError:  # protects against downgrading and updating deleted statuses to errors
                    job_info["error_info"] = "Was previously deleted"

            response["jobs"].append(job_info)

        if not response["jobs"]:
            response["error"] = "No jobs found"

        return response

    except Exception:
        logger.exception("Failed to get jobs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def _get_jobs(con, token, job_ids):
    account_type = token.account_type
    account_id = str(uuid.UUID(token.account_id))

    logger.info(f"Retrieving job info with IDs: {job_ids} for {account_type}: {account_id}")

    # give advanced privileges to access all uploads under customer_id
    # TODO update this to product specific when landing page is specced out more
    if Scopes.MANTARRAY__RW_ALL_DATA in token.scopes:
        account_id = str(uuid.UUID(token.customer_id))
        # catches in the else block like customers in get_uploads, just set here so it's not customer and become confusing
        account_type = "rw_all_user"

    return await get_jobs(con=con, account_type=account_type, account_id=account_id, job_ids=job_ids)


@app.post("/jobs")
async def create_new_job(
    request: Request, details: JobRequest, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE))
):
    try:
        user_id = str(uuid.UUID(token.userid))
        customer_id = str(uuid.UUID(token.customer_id))
        user_scopes = token.scopes
        upload_id = details.upload_id

        bind_context_to_logger({"user_id": user_id, "customer_id": customer_id, "upload_id": str(upload_id)})

        logger.info(f"Creating job for upload {upload_id} with user ID: {user_id}")

        # params to use for all current versions of pulse3d
        params = [
            "baseline_widths_to_use",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
            "max_y",
            "normalize_y_axis",
            "include_stim_protocols",
        ]

        previous_semver_version = (
            VersionInfo.parse(details.previous_version) if details.previous_version else None
        )

        bind_context_to_logger({"version": details.version})

        pulse3d_semver = VersionInfo.parse(details.version)
        use_noise_based_peak_finding = pulse3d_semver >= "0.33.2"

        # TODO see if any of this pertains to deprecated pulse3d versions and can be removed
        # Luci (12/14/2022) PlateRecording.to_dataframe() was updated in 0.28.3 to include 0.0 timepoint so this accounts for the index difference between versions
        peak_valley_diff = 0
        if previous_semver_version is not None and previous_semver_version != pulse3d_semver:
            if previous_semver_version < "0.28.3" and pulse3d_semver >= "0.28.3":
                peak_valley_diff += 1
            elif previous_semver_version >= "0.28.3" and pulse3d_semver < "0.28.3":
                peak_valley_diff -= 1

        if pulse3d_semver >= "0.30.1":
            # Tanner (2/7/23): these params added in earlier versions but there are bugs with using this param in re-analysis prior to 0.30.1
            params += ["stiffness_factor", "inverted_post_magnet_wells"]
        if pulse3d_semver >= "0.30.3":
            params.append("well_groups")
        if pulse3d_semver >= "0.30.5":
            params.append("stim_waveform_format")
        if pulse3d_semver >= "0.34.2":
            params.append("data_type")

        if use_noise_based_peak_finding:
            params += [
                "height_factor",
                "relative_prominence_factor",
                "noise_prominence_factor",
                "max_frequency",
                "valley_search_duration",
                "upslope_duration",
                "upslope_noise_allowance_duration",
            ]
        else:
            params.append("prominence_factors")

        details_dict = dict(details)

        analysis_params = {param: details_dict[param] for param in params}

        if details.peaks_valleys:
            analysis_params["peaks_valleys"] = True

        # convert these params into a format compatible with pulse3D
        for param, default_values in (
            ("prominence_factors", DEFAULT_PROMINENCE_FACTORS),
            (
                "width_factors",
                DEFAULT_NB_WIDTH_FACTORS if use_noise_based_peak_finding else DEFAULT_WIDTH_FACTORS,
            ),
            ("baseline_widths_to_use", DEFAULT_BASELINE_WIDTHS),
        ):
            if param in analysis_params:
                analysis_params[param] = _format_tuple_param(analysis_params[param], default_values)

        logger.info(f"Using v{details.version} with params: {analysis_params}")

        priority = 10
        async with request.state.pgpool.acquire() as con:
            # first check user_id of upload matches user_id in token
            # Luci (12/14/2022) checking separately here because the only other time it's checked is in the pulse3d-worker, we want to catch it here first if it's unauthorized and not checking in create_job to make it universal to all services, not just pulse3d
            # Luci (12/14/2022) customer id is checked already because the customer_id in the token is being used to find upload details
            row = await con.fetchrow("SELECT user_id, type FROM uploads where id=$1", upload_id)
            original_upload_user = str(row["user_id"])
            upload_type = row["type"]

            # check if pulse3d version is available
            # if deprecated and end of life date passed then cancel the upload
            # if end of life date is none then pulse3d version is usable
            pulse3d_version_status = await con.fetchrow(
                "SELECT state, end_of_life_date FROM pulse3d_versions WHERE version = $1", details.version
            )
            status_name = pulse3d_version_status["state"]
            end_of_life_date = pulse3d_version_status["end_of_life_date"]

            if status_name == "deprecated" and (
                end_of_life_date is not None
                and datetime.strptime(end_of_life_date, "%Y-%m-%d") > datetime.now()
            ):
                return GenericErrorResponse(
                    message="Attempted to use pulse3d version that is removed", error="pulse3dVersionError"
                )

            if Scopes.MANTARRAY__RW_ALL_DATA not in user_scopes:
                # if users don't match and they don't have an all_data scope, then raise unauth error
                if user_id != original_upload_user:
                    return GenericErrorResponse(
                        message="User does not have authorization to start this job.",
                        error="AuthorizationError",
                    )

            # second, check usage quota for customer account
            usage_quota = await check_customer_quota(con, customer_id, upload_type)
            if usage_quota["jobs_reached"]:
                return GenericErrorResponse(message=usage_quota, error="UsageError")

            # if a name is present, then add to metadata of job
            job_meta = {"analysis_params": analysis_params, "version": details.version}
            if details.name_override and pulse3d_semver >= "0.32.2":
                job_meta.update({"name_override": details.name_override})

            # finally create job
            job_id = await create_job(
                con=con,
                upload_id=upload_id,
                queue=f"pulse3d-v{details.version}",
                priority=priority,
                meta=job_meta,
                customer_id=customer_id,
                job_type=upload_type,
            )

            bind_context_to_logger({"job_id": str(job_id)})

            # check customer quota after job
            usage_quota = await check_customer_quota(con, customer_id, upload_type)

            # Luci (12/1/22): this happens after the job is already created to have access to the job id, hopefully this doesn't cause any issues with the job starting before the file is uploaded to s3
            if details.peaks_valleys:
                key = (
                    f"uploads/{customer_id}/{original_upload_user}/{upload_id}/{job_id}/peaks_valleys.parquet"
                )
                logger.info(f"Peaks and valleys found in job request, uploading to s3: {key}")

                # only added during interactive analysis
                with tempfile.TemporaryDirectory() as tmpdir:
                    pv_parquet_path = os.path.join(tmpdir, "peaks_valleys.parquet")
                    peak_valleys_dict = dict()

                    # format peaks and valleys to simple df
                    for well, peaks_valleys in details.peaks_valleys.items():
                        for feature_idx, feature_name in enumerate(["peaks", "valleys"]):
                            peak_valleys_dict[f"{well}__{feature_name}"] = (
                                pd.Series(peaks_valleys[feature_idx]) + peak_valley_diff
                            )

                    # write peaks and valleys to parquet file in temporary directory
                    pd.DataFrame(peak_valleys_dict).to_parquet(pv_parquet_path)
                    # upload to s3 under upload id and job id for pulse3d-worker to use
                    upload_file_to_s3(bucket=PULSE3D_UPLOADS_BUCKET, key=key, file=pv_parquet_path)
            else:
                # Luci (12/13/23): if not interactive analysis, kick off second job to test pulse3d rewrite. IA is not setup to work yet.
                await create_job(
                    con=con,
                    upload_id=upload_id,
                    queue="test-pulse3d-v1.0.0rc9",
                    priority=priority,
                    meta=job_meta,
                    customer_id=customer_id,
                    job_type=upload_type,
                    add_to_results=False,
                )

        return JobResponse(
            id=job_id,
            user_id=user_id,
            upload_id=upload_id,
            status="pending",
            priority=priority,
            usage_quota=usage_quota,
        )

    except Exception:
        logger.exception("Failed to create job")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _format_tuple_param(
    options: TupleParam | None, default_values: int | tuple[int, ...]
) -> TupleParam | None:
    if options is None or all(op is None for op in options):
        return None

    if isinstance(default_values, int):
        default_values = (default_values,) * len(options)

    # set any unspecified values to the default value
    # pulse3d does not like float values
    formatted_options = tuple(
        (int(option) if option is not None else default_value)
        for option, default_value in zip(options, default_values)
    )

    return formatted_options


@app.delete("/jobs")
async def soft_delete_jobs(
    request: Request,
    job_ids: list[uuid.UUID] = Query(None),
    token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ)),
):
    # make sure at least one job ID was given
    if not job_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No job IDs given")

    # need to convert UUIDs to str to avoid issues with DB
    job_ids = [str(job_id) for job_id in job_ids]

    try:
        account_id = str(uuid.UUID(token.account_id))

        bind_context_to_logger(
            {"user_id": token.userid, "customer_id": token.customer_id, "job_ids": job_ids}
        )

        async with request.state.pgpool.acquire() as con:
            await delete_jobs(
                con=con, account_type=token.account_type, account_id=account_id, job_ids=job_ids
            )
    except Exception:
        logger.exception("Failed to soft delete jobs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/jobs/download")
async def download_analyses(
    request: Request, details: JobDownloadRequest, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ))
):
    job_ids = details.job_ids
    # make sure at least one job ID was given
    if not job_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No job IDs given")

    # need to convert UUIDs to str to avoid issues with DB
    job_ids = [str(job_id) for job_id in job_ids]

    bind_context_to_logger({"user_id": token.userid, "customer_id": token.customer_id, "job_ids": job_ids})

    try:
        async with request.state.pgpool.acquire() as con:
            jobs = await _get_jobs(con, token, job_ids)

        num_times_repeated = defaultdict(lambda: 0)

        unique_filenames = list()
        keys = list()

        for job in jobs:
            if job["status"] != "finished":
                continue

            obj_key = job["object_key"]
            keys.append(obj_key)

            filename = os.path.basename(obj_key)

            if filename in unique_filenames:
                num_times_repeated[filename] += 1
                duplicate_num = num_times_repeated[filename]
                # add duplicate num to differentiate duplicate filenames
                root, ext = os.path.splitext(filename)
                filename = f"{root}_({duplicate_num}){ext}"

            unique_filenames.append(filename)

        # Grab ZIP file from in-memory, make response with correct MIME-type
        return StreamingResponse(
            content=stream_zip(
                _yield_s3_objects(bucket=PULSE3D_UPLOADS_BUCKET, keys=keys, filenames=unique_filenames)
            ),
            media_type="application/zip",
        )

    except Exception:
        logger.exception("Failed to download analyses")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _yield_s3_objects(bucket: str, keys: list[str], filenames: list[str]):
    # TODO consider moving this to core s3 utils if more routes need to start using it
    try:
        s3 = boto3.session.Session().resource("s3")
        for idx, key in enumerate(keys):
            obj = s3.Object(bucket_name=PULSE3D_UPLOADS_BUCKET, key=key)
            yield filenames[idx], datetime.now(), 0o600, ZIP_64, obj.get()["Body"]

    except Exception as e:
        raise S3Error(f"Failed to access {bucket}/{key}") from e


@app.get("/jobs/waveform-data", response_model=WaveformDataResponse | GenericErrorResponse)
async def get_interactive_waveform_data(
    request: Request,
    upload_id: uuid.UUID = Query(None),
    job_id: uuid.UUID = Query(None),
    token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE)),
):
    account_id = str(uuid.UUID(token.account_id))
    account_type = token.account_type
    is_user = account_type == "user"

    if job_id is None or upload_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required ids to get job metadata."
        )

    upload_id = str(upload_id)
    job_id = str(job_id)

    bind_context_to_logger(
        {"customer_id": token.customer_id, "user_id": token.userid, "upload_id": upload_id, "job_id": job_id}
    )

    try:
        async with request.state.pgpool.acquire() as con:
            logger.info(f"Getting metadata for job {job_id}")
            jobs = await _get_jobs(con, token, [job_id])

        selected_job = jobs[0]
        parsed_meta = json.loads(selected_job["job_meta"])
        recording_owner_id = str(selected_job["user_id"])
        analysis_params = parsed_meta.get("analysis_params", {})
        pulse3d_version = parsed_meta.get("version")

        if Scopes.MANTARRAY__RW_ALL_DATA not in token.scopes and is_user:
            # only allow user to perform interactive analysis on another user's recording if special scope
            # customer id will be checked when attempting to locate file in s3 with customer id found in token
            if recording_owner_id != account_id:
                return GenericErrorResponse(
                    error="AuthorizationError",
                    message="User does not have authorization to start interactive analysis on this recording.",
                )

        # Get presigned url for time force data
        parquet_filename = f"{os.path.splitext(selected_job['filename'])[0]}.parquet"
        parquet_key = (
            f"{selected_job['prefix']}/time_force_data/{pulse3d_version}/{parquet_filename}"
            if pulse3d_version is not None
            else f"{selected_job['prefix']}/time_force_data/{parquet_filename}"
        )

        logger.info(f"Generating presigned URL for {parquet_filename}")
        time_force_url = generate_presigned_url(PULSE3D_UPLOADS_BUCKET, parquet_key)

        # Get presigned url for peaks and valleys
        logger.info("Generating presigned URL for peaks and valleys")
        pv_parquet_key = f"{selected_job['prefix']}/{job_id}/peaks_valleys.parquet"
        peaks_valleys_url = generate_presigned_url(PULSE3D_UPLOADS_BUCKET, pv_parquet_key)

        data_type = analysis_params.get("data_type")
        if not data_type:
            # if data type is not present, is present and is None, or some other falsey value, set to Force as default
            data_type = "Force"

        return WaveformDataResponse(
            time_force_url=time_force_url,
            peaks_valleys_url=peaks_valleys_url,
            amplitude_label=_get_full_amplitude_label(data_type),
        )
    # ValueError gets raised when no object is found in s3 that matches given key
    except ValueError:
        return GenericErrorResponse(
            error="MissingDataError", message="Parquet file was not found in S3. Reanalysis required."
        )
    except S3Error:
        logger.exception("Error from s3")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception:
        logger.exception("Failed to get interactive waveform data")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _get_full_amplitude_label(data_type: str) -> str:
    return CALCULATED_METRIC_DISPLAY_NAMES[AMPLITUDE_UUID].format(
        amplitude=DATA_TYPE_TO_AMPLITUDE_LABEL.get(data_type.lower(), DEFAULT_AMPLITUDE_LABEL),
        unit=DATA_TYPE_TO_UNIT_LABEL.get(data_type.lower(), DEFAULT_UNIT_LABEL),
    )


@app.get("/versions")
async def get_versions(request: Request):
    """Retrieve info of all the active pulse3d releases listed in the DB."""
    try:
        async with request.state.pgpool.acquire() as con:
            # check if the pulse3d version has reached its end of life
            # only deprected versions should have an end of life date, othere wise it is null
            rows = await con.fetch(  # TODO should eventually sort these using a more robust method
                "SELECT version, state, end_of_life_date FROM pulse3d_versions WHERE state != 'deprecated' OR NOW() < end_of_life_date ORDER BY created_at"
            )
        return [dict(row) for row in rows]

    except Exception:
        logger.exception("Failed to retrieve info of pulse3d versions")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/usage", response_model=UsageQuota)
async def get_usage_quota(
    request: Request, service: str = Query(None), token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ))
):
    """Get the usage quota for the specific user"""
    try:
        customer_id = str(uuid.UUID(token.customer_id))

        bind_context_to_logger({"customer_id": customer_id})

        async with request.state.pgpool.acquire() as con:
            usage_quota = await check_customer_quota(con, customer_id, service)
            return usage_quota
    except Exception:
        logger.exception("Failed to fetch quota usage")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/presets")
async def save_analysis_presets(
    request: Request, details: SavePresetRequest, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE))
):
    """Save analysis parameter preset for user"""
    try:
        user_id = str(uuid.UUID(token.userid))
        customer_id = str(uuid.UUID(token.customer_id))
        bind_context_to_logger({"customer_id": customer_id, "user_id": user_id})

        async with request.state.pgpool.acquire() as con:
            return await create_analysis_preset(con, user_id, details)
    except Exception:
        logger.exception("Failed to save analysis preset for user")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/presets")
async def get_analysis_presets(request: Request, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE))):
    """Get analysis parameter preset for user"""
    try:
        user_id = str(uuid.UUID(token.userid))
        customer_id = str(uuid.UUID(token.customer_id))
        bind_context_to_logger({"customer_id": customer_id, "user_id": user_id})

        async with request.state.pgpool.acquire() as con:
            async with con.transaction():
                return [
                    dict(row)
                    async for row in con.cursor(
                        "SELECT name, parameters FROM analysis_presets where user_id=$1", user_id
                    )
                ]

    except Exception:
        logger.exception("Failed to get analysis presets for user")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
