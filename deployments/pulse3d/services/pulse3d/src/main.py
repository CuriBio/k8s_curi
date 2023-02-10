from collections import defaultdict
import json
import logging
from typing import List, Optional, Tuple, Union
import uuid
import tempfile
import boto3
import os
import pandas as pd
from glob import glob
from semver import VersionInfo
import numpy as np

from stream_zip import ZIP_64, stream_zip
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pulse3D.peak_detection import peak_detector
from pulse3D.constants import (
    DEFAULT_BASELINE_WIDTHS,
    DEFAULT_PROMINENCE_FACTORS,
    MICRO_TO_BASE_CONVERSION,
    DEFAULT_WIDTH_FACTORS,
)

from auth import ProtectedAny, PULSE3D_USER_SCOPES, PULSE3D_SCOPES, split_scope_account_data
from core.config import DATABASE_URL, PULSE3D_UPLOADS_BUCKET, MANTARRAY_LOGS_BUCKET, DASHBOARD_URL
from jobs import (
    create_upload,
    create_job,
    get_uploads,
    get_jobs,
    delete_jobs,
    delete_uploads,
    check_customer_quota,
)
from models.models import (
    UploadRequest,
    UploadResponse,
    JobRequest,
    JobResponse,
    JobDownloadRequest,
    WaveformDataResponse,
    UploadDownloadRequest,
    GenericErrorResponse,
)
from models.types import TupleParam

from utils.db import AsyncpgPoolDep
from utils.s3 import (
    generate_presigned_post,
    generate_presigned_url,
    S3Error,
    download_directory_from_s3,
    upload_file_to_s3,
)

# logging is configured in log_config.yaml
logger = logging.getLogger(__name__)

app = FastAPI(openapi_url=None)
asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[DASHBOARD_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# TODO move this to core lib
def _is_valid_well_name(well_name):
    return (
        isinstance(well_name, str)
        and len(well_name) == 2
        and well_name[0] in ("A", "B", "C", "D")
        and well_name[1] in [str(n) for n in range(1, 7)]
    )


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.pgpool = await asyncpg_pool()
    response = await call_next(request)
    return response


@app.on_event("startup")
async def startup():
    await asyncpg_pool()


# TODO define response model
@app.get("/uploads")
async def get_info_of_uploads(
    request: Request,
    upload_ids: Optional[List[uuid.UUID]] = Query(None),
    token=Depends(ProtectedAny(scope=PULSE3D_SCOPES)),
):
    # need to convert to UUIDs to str to avoid issues with DB
    if upload_ids:
        upload_ids = [str(upload_id) for upload_id in upload_ids]

    try:
        account_id = str(uuid.UUID(token["userid"]))
        account_type = token["account_type"]

        # give advanced privileges to access all uploads under customer_id
        if "pulse3d:rw_all_data" in token["scope"]:
            account_id = str(uuid.UUID(token["customer_id"]))
            # catches in the else block like customers in get_uploads, just set here so it's not customer and become confusing
            account_type = "dataUser"

        async with request.state.pgpool.acquire() as con:
            uploads = await get_uploads(
                con=con, account_type=account_type, account_id=account_id, upload_ids=upload_ids
            )
            if account_type != "customer":
                # customer accounts don't matter here because they don't have the ability to delete
                for upload in uploads:
                    # need way on FE to tell if user owns recordings besides username since current user's username is not stored on the FE. We want to prevent users from attempting to delete files that aren't theirs before calling /delete route
                    upload["owner"] = str(upload["user_id"]) == str(uuid.UUID(token["userid"]))

            return uploads

    except Exception as e:
        logger.exception(f"Failed to get uploads: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/uploads", response_model=Union[UploadResponse, GenericErrorResponse])
async def create_recording_upload(
    request: Request,
    details: UploadRequest,
    token=Depends(ProtectedAny(scope=PULSE3D_USER_SCOPES)),
):
    try:
        user_id = str(uuid.UUID(token["userid"]))
        customer_id = str(uuid.UUID(token["customer_id"]))
        service, _ = split_scope_account_data(token["scope"][0])

        upload_params = {
            "prefix": f"uploads/{customer_id}/{user_id}/{{upload_id}}",
            "filename": details.filename,
            "md5": details.md5s,
            "user_id": user_id,
            "type": details.upload_type,
            "customer_id": customer_id,
        }
        async with request.state.pgpool.acquire() as con:
            usage_quota = await check_customer_quota(con, customer_id, service)
            if usage_quota["uploads_reached"]:
                return GenericErrorResponse(message=usage_quota, error="UsageError")

            # Tanner (7/5/22): using a transaction here so that if _generate_presigned_post fails
            # then the new upload row won't be committed
            async with con.transaction():
                upload_id = await create_upload(con=con, upload_params=upload_params)

                params = _generate_presigned_post(
                    user_id,
                    customer_id,
                    details,
                    PULSE3D_UPLOADS_BUCKET,
                    upload_id=upload_id,
                )
                return UploadResponse(id=upload_id, params=params)
    except S3Error as e:
        logger.exception(str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(repr(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.delete("/uploads")
async def soft_delete_uploads(
    request: Request,
    upload_ids: List[uuid.UUID] = Query(None),
    token=Depends(ProtectedAny(scope=PULSE3D_SCOPES)),
):
    # make sure at least one upload ID was given
    if not upload_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No upload IDs given")
    # need to convert UUIDs to str to avoid issues with DB
    upload_ids = [str(upload_id) for upload_id in upload_ids]

    try:
        account_id = str(uuid.UUID(token["userid"]))
        async with request.state.pgpool.acquire() as con:
            await delete_uploads(
                con=con, account_type=token["account_type"], account_id=account_id, upload_ids=upload_ids
            )
    except Exception as e:
        logger.error(repr(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/uploads/download")
async def download_zip_files(
    request: Request,
    details: UploadDownloadRequest,
    token=Depends(ProtectedAny(scope=PULSE3D_SCOPES)),
):
    upload_ids = details.upload_ids

    # make sure at least one job ID was given
    if not upload_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No upload IDs given")

    # need to convert UUIDs to str to avoid issues with DB
    upload_ids = [str(id) for id in upload_ids]
    account_id = str(uuid.UUID(token["userid"]))
    account_type = token["account_type"]

    # give advanced privileges to access all uploads under customer_id
    if "pulse3d:rw_all_data" in token["scope"]:
        account_id = str(uuid.UUID(token["customer_id"]))
        account_type = "dataUser"

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

    except Exception as e:
        logger.error(f"Failed to download recording files: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# TODO Tanner (4/21/22): probably want to move this to a more general svc (maybe in apiv2-dep) dedicated to uploading misc files to s3
@app.post("/logs")
async def create_log_upload(
    request: Request,
    details: UploadRequest,
    token=Depends(ProtectedAny(scope=PULSE3D_USER_SCOPES)),
):
    try:
        user_id = str(uuid.UUID(token["userid"]))
        customer_id = str(uuid.UUID(token["customer_id"]))
        params = _generate_presigned_post(user_id, customer_id, details, MANTARRAY_LOGS_BUCKET)
        return UploadResponse(params=params)
    except S3Error as e:
        logger.exception(str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(repr(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _generate_presigned_post(user_id, customer_id, details, bucket, upload_id=None):
    key = f"uploads/{customer_id}/{user_id}/"
    if upload_id:
        key += f"{upload_id}/"
    key += details.filename
    logger.info(f"Generating presigned upload url for {bucket}/{key}")
    params = generate_presigned_post(bucket=bucket, key=key, md5s=details.md5s)
    return params


# TODO create response model
@app.get("/jobs")
async def get_info_of_jobs(
    request: Request,
    job_ids: Optional[List[uuid.UUID]] = Query(None),
    download: bool = Query(True),
    token=Depends(ProtectedAny(scope=PULSE3D_SCOPES)),
):
    # need to convert UUIDs to str to avoid issues with DB
    if job_ids:
        job_ids = [str(job_id) for job_id in job_ids]

    try:
        user_id = str(uuid.UUID(token["userid"]))
        account_type = token["account_type"]

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

            if account_type != "customer":
                # customer accounts don't have the ability to delete so doesn't need this key:value
                # need way on FE to tell if user owns recordings besides username since current user's username is not stored on the FE. We want to prevent users from attempting to delete files that aren't theirs before calling /delete route
                job_info["owner"] = str(job["user_id"]) == user_id

            if job_info["status"] == "finished" and download:
                # This is in case any current users uploaded files before object_key was dropped from uploads table and added to jobs_result
                if obj_key:
                    logger.info(f"Generating presigned download url for {obj_key}")
                    try:
                        job_info["url"] = generate_presigned_url(PULSE3D_UPLOADS_BUCKET, obj_key)
                    except Exception as e:
                        logger.error(f"Error generating presigned url for {obj_key}: {str(e)}")
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

    except Exception as e:
        logger.error(f"Failed to get jobs: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def _get_jobs(con, token, job_ids):
    account_type = token["account_type"]
    account_id = str(uuid.UUID(token["userid"]))

    logger.info(f"Retrieving job info with IDs: {job_ids} for {account_type}: {account_id}")

    # give advanced privileges to access all uploads under customer_id
    if "pulse3d:rw_all_data" in token["scope"]:
        account_id = str(uuid.UUID(token["customer_id"]))
        # catches in the else block like customers in get_uploads, just set here so it's not customer and become confusing
        account_type = "dataUser"

    return await get_jobs(con=con, account_type=account_type, account_id=account_id, job_ids=job_ids)


@app.post("/jobs")
async def create_new_job(
    request: Request,
    details: JobRequest,
    token=Depends(ProtectedAny(scope=PULSE3D_USER_SCOPES)),
):
    try:
        user_id = str(uuid.UUID(token["userid"]))
        customer_id = str(uuid.UUID(token["customer_id"]))
        user_scopes = token["scope"]
        service, _ = split_scope_account_data(user_scopes[0])
        logger.info(f"Creating {service} job for upload {details.upload_id} with user ID: {user_id}")

        params = [
            "baseline_widths_to_use",
            "prominence_factors",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
        ]

        previous_semver_version = (
            VersionInfo.parse(details.previous_version) if details.previous_version else None
        )

        pulse3d_semver = VersionInfo.parse(details.version)

        # Luci (12/14/2022) PlateRecording.to_dataframe() was updated in 0.28.3 to include 0.0 timepoint so this accounts for the index difference between versions
        peak_valley_diff = 0
        if previous_semver_version is not None and previous_semver_version != pulse3d_semver:
            if previous_semver_version < "0.28.3" and pulse3d_semver >= "0.28.3":
                peak_valley_diff += 1
            elif previous_semver_version >= "0.28.3" and pulse3d_semver < "0.28.3":
                peak_valley_diff -= 1

        # don't add params unless the selected pulse3d version supports it
        if pulse3d_semver >= "0.25.0":
            params.append("max_y")
        if pulse3d_semver >= "0.25.4":
            params.append("normalize_y_axis")
        if pulse3d_semver >= "0.28.1":
            params.append("include_stim_protocols")
        if "0.28.2" > pulse3d_semver >= "0.25.2":
            params.append("peaks_valleys")
        if pulse3d_semver >= "0.30.1":
            # Tanner (2/7/23): these params added in earlier versions but there are bugs with using this param in re-analysis prior to 0.30.1
            params.append("stiffness_factor")
            params.append("inverted_post_magnet_wells")

        details_dict = dict(details)

        # Luci (12/14/2022) the index difference needs to be added here because analyses run with versions < 0.28.2 need to be changed before getting added to the job queue. These jobs have the peaks and valleys added to the analysis params, later versions will be added to parquet file in s3
        if details.peaks_valleys:
            for well, peaks_valleys in details.peaks_valleys.items():
                details_dict["peaks_valleys"][well] = [
                    [p + peak_valley_diff for p in peaks_valleys[0]],
                    [v + peak_valley_diff for v in peaks_valleys[1]],
                ]

        analysis_params = {param: details_dict[param] for param in params}

        # Luci (12/14/2022) you don't want to replace the peaks and valleys in details_dict or details because the peaks and valleys will be used later so adding to analysis params here
        if pulse3d_semver >= "0.28.2" and details.peaks_valleys:
            # Luci (12/10/22): this param set to True is used to signify to the FE that peaks and valleys have been edited to display under the analysis params column in the uploads table, but don't append actual peaks and valleys to prevent cluttering the database with large lists
            analysis_params["peaks_valleys"] = True
        # convert these params into a format compatible with pulse3D
        for param, default_values in (
            ("prominence_factors", DEFAULT_PROMINENCE_FACTORS),
            ("width_factors", DEFAULT_WIDTH_FACTORS),
            ("baseline_widths_to_use", DEFAULT_BASELINE_WIDTHS),
        ):
            analysis_params[param] = _format_tuple_param(analysis_params[param], default_values)

        logger.info(f"Using v{details.version} with params: {analysis_params}")

        priority = 10
        async with request.state.pgpool.acquire() as con:
            # first check user_id of upload matches user_id in token
            # Luci (12/14/2022) checking separately here because the only other time it's checked is in the pulse3d-worker, we want to catch it here first if it's unauthorized and not checking in create_job to make it universal to all services, not just pulse3d
            # Luci (12/14/2022) customer id is checked already because the customer_id in the token is being used to find upload details
            if "pulse3d:rw_all_data" not in user_scopes:
                row = await con.fetchrow("SELECT user_id FROM uploads where id=$1", details.upload_id)
                # if users don't match and they don't have an all_data scope, then raise unauth error
                if user_id != str(row["user_id"]):
                    return GenericErrorResponse(
                        message="User does not have authorization to start this job.",
                        error="AuthorizationError",
                    )

            # second, check usage quota for customer account
            usage_quota = await check_customer_quota(con, customer_id, service)
            if usage_quota["jobs_reached"]:
                return GenericErrorResponse(message=usage_quota, error="UsageError")

            # finally create job
            job_id = await create_job(
                con=con,
                upload_id=details.upload_id,
                queue=f"pulse3d-v{details.version}",
                priority=priority,
                meta={"analysis_params": analysis_params, "version": details.version},
                customer_id=customer_id,
                job_type=service,
            )

            # Luci (12/1/22): this happens after the job is already created to have access to the job id, hopefully this doesn't cause any issues with the job starting before the file is uploaded to s3
            # Versions less than 0.28.2 should not be in the dropdown as an option, this is just an extra check for versions greater than 0.28.2
            if details.peaks_valleys and pulse3d_semver >= "0.28.2":
                key = f"uploads/{customer_id}/{user_id}/{details.upload_id}/{job_id}/peaks_valleys.parquet"
                logger.info(f"Peaks and valleys found in job request, uploading to s3: {key}")

                # only added during interactive analysis
                with tempfile.TemporaryDirectory() as tmpdir:
                    pv_parquet_path = os.path.join(tmpdir, "peaks_valleys.parquet")
                    peak_valleys_dict = dict()
                    # format peaks and valleys to simple df
                    for well, peaks_valleys in details_dict["peaks_valleys"].items():
                        peak_valleys_dict[f"{well}__peaks"] = pd.Series(peaks_valleys[0])
                        peak_valleys_dict[f"{well}__valleys"] = pd.Series(peaks_valleys[1])

                    # write peaks and valleys to parquet file in temporary directory
                    pd.DataFrame(peak_valleys_dict).to_parquet(pv_parquet_path)
                    # upload to s3 under upload id and job id for pulse3d-worker to use
                    upload_file_to_s3(bucket=PULSE3D_UPLOADS_BUCKET, key=key, file=pv_parquet_path)

        return JobResponse(
            id=job_id,
            user_id=user_id,
            upload_id=details.upload_id,
            status="pending",
            priority=priority,
            usage_quota=usage_quota,
        )
    except Exception as e:
        logger.exception(f"Failed to create job: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _format_tuple_param(
    options: Optional[TupleParam], default_values: Union[int, Tuple[int, ...]]
) -> Optional[TupleParam]:
    if options is None or all(op is None for op in options):
        return None

    if isinstance(default_values, int):
        default_values = (default_values,) * len(options)

    # set any unspecified values to the default value
    formatted_options = tuple(
        (option if option is not None else default_value)
        for option, default_value in zip(options, default_values)
    )

    return formatted_options


@app.delete("/jobs")
async def soft_delete_jobs(
    request: Request,
    job_ids: List[uuid.UUID] = Query(None),
    token=Depends(ProtectedAny(scope=PULSE3D_SCOPES)),
):
    # make sure at least one job ID was given
    if not job_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No job IDs given")

    # need to convert UUIDs to str to avoid issues with DB
    job_ids = [str(job_id) for job_id in job_ids]

    try:
        account_id = str(uuid.UUID(token["userid"]))
        async with request.state.pgpool.acquire() as con:
            await delete_jobs(
                con=con, account_type=token["account_type"], account_id=account_id, job_ids=job_ids
            )
    except Exception as e:
        logger.error(f"Failed to soft delete jobs: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/jobs/download")
async def download_analyses(
    request: Request,
    details: JobDownloadRequest,
    token=Depends(ProtectedAny(scope=PULSE3D_SCOPES)),
):
    job_ids = details.job_ids

    # make sure at least one job ID was given
    if not job_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No job IDs given")

    # need to convert UUIDs to str to avoid issues with DB
    job_ids = [str(job_id) for job_id in job_ids]

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

    except Exception as e:
        logger.error(f"Failed to download analyses: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _yield_s3_objects(bucket: str, keys: List[str], filenames: List[str]):
    # TODO consider moving this to core s3 utils if more routes need to start using it
    try:
        s3 = boto3.session.Session().resource("s3")
        for idx, key in enumerate(keys):
            obj = s3.Object(bucket_name=PULSE3D_UPLOADS_BUCKET, key=key)
            yield filenames[idx], datetime.now(), 0o600, ZIP_64, obj.get()["Body"]

    except Exception as e:
        raise S3Error(f"Failed to access {bucket}/{key}: {repr(e)}")


@app.get("/jobs/waveform_data", response_model=Union[WaveformDataResponse, GenericErrorResponse])
async def get_interactive_waveform_data(
    request: Request,
    upload_id: uuid.UUID = Query(None),
    job_id: uuid.UUID = Query(None),
    token=Depends(ProtectedAny(scope=PULSE3D_USER_SCOPES)),
):

    account_id = str(uuid.UUID(token["userid"]))
    customer_id = str(uuid.UUID(token["customer_id"]))

    if job_id is None or upload_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required ids to get job metadata."
        )

    upload_id = str(upload_id)
    job_id = str(job_id)

    try:
        async with request.state.pgpool.acquire() as con:
            logger.info(f"Getting metadata for job {job_id}")
            jobs = await _get_jobs(con, token, [job_id])

        selected_job = jobs[0]
        parsed_meta = json.loads(selected_job["job_meta"])
        recording_owner_id = str(selected_job["user_id"])
        analysis_params = parsed_meta.get("analysis_params")
        pulse3d_version = parsed_meta.get("version")

        if "pulse3d:rw_all_data" not in token["scope"]:
            # only allow user to perform interactive analysis on another user's recording if special scope
            # customer id will be checked when attempting to locate file in s3 with customer id found in token
            if recording_owner_id != account_id:
                return GenericErrorResponse(
                    error="AuthorizationError",
                    message="User does not have authorization to start interactive analysis on this recording.",
                )

        # TODO should make a function in core that handles running peak_detector or loading peaks/valleys from parquet and import it here and in the pulse3d-worker

        with tempfile.TemporaryDirectory() as tmpdir:
            key = f"uploads/{customer_id}/{recording_owner_id}/{upload_id}"
            logger.info(f"Downloading recording data from {key}")
            download_directory_from_s3(bucket=PULSE3D_UPLOADS_BUCKET, key=key, file_path=tmpdir)

            parquet_path = None
            # check if time force parquet file is found under pulse3d version prefix first
            if pulse3d_version is not None:
                # read the time force dataframe from the parquet file
                parquet_path = glob(
                    os.path.join(tmpdir, "time_force_data", pulse3d_version, "*.parquet"), recursive=True
                )
            # if no pulse3d version specified in the job metadata or no time force parquet file was found
            # by previous glob, check s3 without pulse3d prefix
            if not parquet_path:
                parquet_path = glob(os.path.join(tmpdir, "time_force_data", "*.parquet"), recursive=True)
            # if parquet file is still not found, return error msg. this will occur for any files analyzed
            # before this release. Ask user to perform reanalysis again on most recent pulse3d
            if not parquet_path:
                return GenericErrorResponse(
                    error="MissingDataError",
                    message="Time force parquet file was not found. Reanalysis required.",
                )

            # if file found, read to dataframe for IA
            time_force_df = pd.read_parquet(parquet_path)

            logger.info("Checking for peaks and valleys in S3")
            pv_parquet_path = glob(os.path.join(tmpdir, job_id, "*.parquet"), recursive=True)

            # Luci (12/14/2022) peaks_valleys will be none when interactive analysis is being run for the first time on the original analysis. There won't be any peaks or valleys found because nothing has been altered yet
            peaks_valleys_needed = len(pv_parquet_path) == 0 and analysis_params.get("peaks_valleys") is None

            if not peaks_valleys_needed:
                peak_valleys_df = pd.read_parquet(pv_parquet_path)

            # remove raw data columns
            # the any conditional is for testing, the __raw always needs to be excluded
            columns = [
                c for c in time_force_df.columns if not any(x in c for x in ("__raw", "__peaks", "__valleys"))
            ]
            # this is to handle analyses run before PR.to_dataframe() where time is in seconds
            needs_unit_conversion = not [c for c in time_force_df.columns if "__raw" in c]
            time = time_force_df[columns[0]].tolist()

            # set up empty dictionaries to be passed in response
            coordinates = dict()
            peaks_and_valleys = dict()
            for well in columns:
                if not _is_valid_well_name(well):
                    continue

                well_force = time_force_df[well].dropna().tolist()
                if peaks_valleys_needed:
                    if needs_unit_conversion:
                        # not exact, but this isn't used outside of graphing in FE, real raw data doesn't get changed
                        min_value = min(well_force)
                        well_force -= min_value
                        well_force *= MICRO_TO_BASE_CONVERSION
                        time = [i * MICRO_TO_BASE_CONVERSION for i in time]

                    interpolated_well_data = np.row_stack([time[: len(well_force)], well_force])

                    peak_detector_params = {
                        param: analysis_params[param]
                        for param in ("prominence_factors", "width_factors", "start_time", "end_time")
                        if analysis_params[param] is not None
                    }

                    peaks, valleys = peak_detector(interpolated_well_data, **peak_detector_params)
                    # needs to be converted to lists to be sent as json in response
                    peaks_and_valleys[well] = [peaks.tolist(), valleys.tolist()]

                elif len(pv_parquet_path) == 1:
                    # need to remove nan values becuase peaks and valleys are different length lists
                    peaks = peak_valleys_df[f"{well}__peaks"].dropna().tolist()
                    valleys = peak_valleys_df[f"{well}__valleys"].dropna().tolist()
                    # stored as floats in df so need to convert to int
                    peaks_and_valleys[well] = [[int(x) for x in peaks], [int(x) for x in valleys]]
                    logger.info(f"{len(peaks)} peaks and {len(valleys)} valleys for well {well}")

                coordinates[well] = [
                    [time[i] / MICRO_TO_BASE_CONVERSION, val] for i, val in enumerate(well_force)
                ]

            # Luci (12/14/2022) analysis_params["peaks_valleys"] will be a dictionary in version < 0.28.2 when peaks and valleys are only stored in this db column and not in s3
            if analysis_params.get("peaks_valleys") is not None and isinstance(
                analysis_params["peaks_valleys"], dict
            ):
                peaks_and_valleys = analysis_params["peaks_valleys"]

            return WaveformDataResponse(coordinates=coordinates, peaks_valleys=peaks_and_valleys)

    except S3Error as e:
        logger.error(f"Error from s3: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Failed to get interactive waveform data: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/versions")
async def get_versions(request: Request):
    """Retrieve info of all the active pulse3d releases listed in the DB."""
    try:
        async with request.state.pgpool.acquire() as con:
            rows = await con.fetch(  # TODO should eventually sort these using a more robust method
                "SELECT version, state FROM pulse3d_versions WHERE state != 'deprecated' ORDER BY created_at"
            )

        return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Failed to retrieve info of pulse3d versions: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
