from contextlib import asynccontextmanager
from collections import defaultdict
from datetime import datetime
import json
import os
import tempfile
import time
from typing import Any
import uuid
from zoneinfo import ZoneInfo

import polars as pl
import structlog
from auth import (
    Scopes,
    ScopeTags,
    ProtectedAny,
    check_prohibited_product,
    ProhibitedProductError,
    get_product_tags_of_user,
)
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from jobs import (
    check_customer_pulse3d_usage,
    create_analysis_preset,
    create_job,
    create_upload,
    delete_jobs,
    delete_uploads,
    get_uploads_info_for_base_user,
    get_uploads_info_for_rw_all_data_user,
    get_uploads_info_for_admin,
    get_uploads_download_info_for_base_user,
    get_uploads_download_info_for_rw_all_data_user,
    get_uploads_download_info_for_admin,
    get_jobs_of_uploads_for_base_user,
    get_jobs_of_uploads_for_rw_all_data_user,
    get_jobs_of_uploads_for_admin,
    get_jobs_download_info_for_base_user,
    get_jobs_download_info_for_rw_all_data_user,
    get_jobs_download_info_for_admin,
    get_job_waveform_data_for_base_user,
    get_job_waveform_data_for_rw_all_data_user,
    get_job_waveform_data_for_admin_user,
    get_legacy_jobs_info_for_user,
    get_jobs_info_for_base_user,
    get_jobs_info_for_rw_all_data_user,
    get_jobs_info_for_admin,
)
from pulse3D.constants import DataTypes
from pulse3D.peak_finding.constants import (
    DefaultLegacyPeakFindingParams,
    DefaultNoiseBasedPeakFindingParams,
    FeatureMarkers,
)
from pulse3D.peak_finding.utils import create_empty_df, mark_features
from pulse3D.metrics.constants import TwitchMetrics, DefaultMetricsParams
from pulse3D.rendering.utils import get_metric_display_title
from semver import VersionInfo
from stream_zip import stream_zip
from starlette_context import context, request_cycle_context
from structlog.contextvars import bind_contextvars, clear_contextvars
from utils.db import AsyncpgPoolDep
from utils.logging import setup_logger, bind_context_to_logger
from utils.s3 import (
    S3Error,
    generate_presigned_post,
    generate_presigned_url,
    upload_file_to_s3,
    yield_s3_objects,
)
from uvicorn.protocols.utils import get_path_with_query_string

from core.config import DASHBOARD_URL, DATABASE_URL, MANTARRAY_LOGS_BUCKET, PULSE3D_UPLOADS_BUCKET
from models.models import (
    GenericErrorResponse,
    JobDownloadRequest,
    JobRequest,
    GetJobsInfoRequest,
    JobResponse,
    NotificationMessageResponse,
    NotificationResponse,
    SaveNotificationRequest,
    SaveNotificationResponse,
    SavePresetRequest,
    UploadDownloadRequest,
    UploadRequest,
    UploadResponse,
    UsageQuota,
    ViewNotificationMessageRequest,
    ViewNotificationMessageResponse,
    WaveformDataResponse,
    GetJobsRequest,
)
from models.types import TupleParam
from repository.notification_repository import NotificationRepository
from service.notification_service import NotificationService

setup_logger()
logger = structlog.stdlib.get_logger("api.access")


asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)
notification_service: NotificationService


@asynccontextmanager
async def lifespan(app: FastAPI):
    global notification_service
    notification_service = NotificationService(NotificationRepository(await asyncpg_pool()))
    yield


app = FastAPI(openapi_url=None, lifespan=lifespan)

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


# TODO define response model
@app.get("/uploads")
async def get_uploads_info(
    request: Request,
    upload_type: str | None = Query(None),
    sort_field: str | None = Query(None),
    sort_direction: str | None = Query(None),
    skip: int = Query(0),
    limit: int = Query(300),
    token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ)),
):
    if token.account_type == "user" and upload_type not in get_product_tags_of_user(token.scopes):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    filters = {
        filter_name: request.query_params[filter_name]
        for filter_name in (
            "filename",
            "id",
            "created_at_min",
            "created_at_max",
            "last_analyzed_min",
            "last_analyzed_max",
            "username",
        )
        if filter_name in request.query_params
    }

    try:
        bind_context_to_logger({"user_id": token.userid, "customer_id": token.customer_id})

        async with request.state.pgpool.acquire() as con:
            return await _get_uploads(
                con=con,
                token=token,
                upload_type=upload_type,
                sort_field=sort_field,
                sort_direction=sort_direction,
                skip=skip,
                limit=limit,
                **filters,
            )

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
            usage_quota = await check_customer_pulse3d_usage(con, customer_id, upload_type)
            if usage_quota["uploads_reached"]:
                return GenericErrorResponse(message=usage_quota, error="UsageError")

            # Tanner (7/5/22): using a transaction here so that if _generate_presigned_post fails
            # then the new upload row won't be committed
            async with con.transaction():
                upload_id = await create_upload(con=con, upload_params=upload_params)
                params = _generate_presigned_post(details, PULSE3D_UPLOADS_BUCKET, s3_key)
                return UploadResponse(id=upload_id, params=params)
    except ProhibitedProductError:
        logger.exception(f"User does not have permission to upload {upload_type} recordings")
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
    token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE)),
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
async def download_uploads(
    request: Request, details: UploadDownloadRequest, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ))
):
    if token.account_type == "user" and details.upload_type not in get_product_tags_of_user(token.scopes):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    # make sure at least one job ID was given
    if not details.upload_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No upload IDs given")

    # need to convert UUIDs to str to avoid issues with DB
    upload_ids = [str(id) for id in details.upload_ids]

    bind_context_to_logger(
        {
            "user_id": token.userid,
            "customer_id": token.customer_id,
            "upload_ids": upload_ids,
            "upload_type": details.upload_type,
        }
    )

    try:
        async with request.state.pgpool.acquire() as con:
            uploads = await _get_uploads_download(
                con=con, token=token, upload_ids=upload_ids, upload_type=details.upload_type
            )

        if isinstance(uploads, GenericErrorResponse):
            return uploads

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
                    yield_s3_objects(bucket=PULSE3D_UPLOADS_BUCKET, keys=keys, filenames=filenames)
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


# TODO Tanner (5/30/24): not sure what to call this since POST /jobs already exists. This needs to be a post route since get routes can't have a body
@app.post("/jobs/info")
async def get_jobs_info(
    request: Request, details: GetJobsInfoRequest, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ))
):
    if token.account_type == "user" and details.upload_type not in get_product_tags_of_user(token.scopes):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    # need to convert UUIDs to str to avoid issues with DB
    upload_ids = [str(upload_id) for upload_id in details.upload_ids]

    try:
        bind_context_to_logger({"user_id": token.userid, "customer_id": token.customer_id})

        async with request.state.pgpool.acquire() as con:
            return await _get_jobs_of_uploads(
                con, token, upload_ids=upload_ids, upload_type=details.upload_type
            )
    except Exception:
        logger.exception("Failed to get jobs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# TODO (9/5/24): should update MA Controller so it does not depend on the legacy version of this route.
# It can use the new version to poll the job results and /jobs/download to download the job
@app.get("/jobs")
async def get_info_of_jobs(
    request: Request,
    model: GetJobsRequest = Depends(),
    token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ)),
):
    if model.legacy:
        return await _legacy_get_info_of_jobs(request, model.job_ids, model.download, token)

    try:
        bind_context_to_logger({"user_id": token.userid, "customer_id": token.customer_id})

        if token.account_type == "user" and model.upload_type not in get_product_tags_of_user(token.scopes):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product type")

        async with request.state.pgpool.acquire() as con:
            return await _get_jobs_info(con, token, **model.model_dump(exclude_none=True))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to get jobs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def _legacy_get_info_of_jobs(request: Request, job_ids: list[uuid.UUID] | None, download: bool, token):
    if not job_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    # need to convert UUIDs to str to avoid issues with DB
    job_ids = [str(job_id) for job_id in job_ids]  # type: ignore

    try:
        bind_context_to_logger(
            {"user_id": token.userid, "customer_id": token.customer_id, "job_ids": job_ids}
        )

        async with request.state.pgpool.acquire() as con:
            jobs = await _get_legacy_jobs_info(con, token, job_ids=job_ids)  # type: ignore

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
                "user_id": job["user_id"],
            }

            # TODO (9/5/24): consider removing the download option here since there is a new route specifically for downloading jobs.
            # This would require updating the MA Controller to use the new route for downloading
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
        logger.exception("Failed to get jobs (legacy)")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/jobs")
async def create_new_job(
    request: Request, details: JobRequest, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE))
):
    try:
        user_id = str(uuid.UUID(token.userid))
        customer_id = str(uuid.UUID(token.customer_id))
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
        if previous_semver_version is not None and previous_semver_version < "0.28.3":
            peak_valley_diff = 1

        if pulse3d_semver >= "0.30.1":
            # Tanner (2/7/23): these params added in earlier versions but there are bugs with using this param in re-analysis prior to 0.30.1
            params += ["stiffness_factor", "inverted_post_magnet_wells"]
        if pulse3d_semver >= "0.30.3":
            params.append("well_groups")
        if pulse3d_semver >= "0.30.5":
            params.append("stim_waveform_format")
        if pulse3d_semver >= "0.34.2":
            params.append("data_type")
        if pulse3d_semver >= "1.0.0":
            params.append("normalization_method")
            params.append("detrend")

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
            ("prominence_factors", DefaultLegacyPeakFindingParams.PROMINENCE_FACTORS.value),
            (
                "width_factors",
                (
                    DefaultNoiseBasedPeakFindingParams.WIDTH_FACTORS.value
                    if use_noise_based_peak_finding
                    else DefaultLegacyPeakFindingParams.WIDTH_FACTORS.value
                ),
            ),
            ("baseline_widths_to_use", DefaultMetricsParams.BASELINE_WIDTHS.value),
        ):
            allow_float = param != "baseline_widths_to_use"
            if param in analysis_params:
                analysis_params[param] = _format_tuple_param(
                    analysis_params[param], default_values, allow_float
                )

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
                "SELECT state, end_of_life_date FROM pulse3d_versions WHERE version=$1", details.version
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

            # if the upload does not belong to this user, make sure this user has the rw_all_scope for this upload type
            if user_id != original_upload_user and upload_type not in get_product_tags_of_user(
                token.scopes, rw_all_only=True
            ):
                return GenericErrorResponse(
                    message=f"User does not have authorization to run jobs for {upload_type} uploads of other users.",
                    error="AuthorizationError",
                )

            # second, check usage quota for customer
            usage_quota = await check_customer_pulse3d_usage(con, customer_id, upload_type)
            if usage_quota["jobs_reached"]:
                return GenericErrorResponse(message=usage_quota, error="UsageError")

            version = details.version

            job_meta = {"analysis_params": analysis_params, "version": version}
            # if a name is present, then add to metadata of job
            if details.name_override and pulse3d_semver >= "0.32.2":
                job_meta["name_override"] = details.name_override

            # finally create job
            job_id = await create_job(
                con=con,
                upload_id=upload_id,
                queue=f"pulse3d-v{version}",
                priority=priority,
                meta=job_meta,
                customer_id=customer_id,
                job_type=upload_type,
            )

            bind_context_to_logger({"job_id": str(job_id)})

            # check customer quota after job
            usage_quota = await check_customer_pulse3d_usage(con, customer_id, upload_type)

            # Luci (12/1/22): this happens after the job is already created to have access to the job id, hopefully this doesn't cause any issues with the job starting before the file is uploaded to s3
            if details.peaks_valleys:
                key = (
                    f"uploads/{customer_id}/{original_upload_user}/{upload_id}/{job_id}/peaks_valleys.parquet"
                )
                logger.info(f"Peaks and valleys found in job request, uploading to s3: {key}")

                # only added during interactive analysis
                with tempfile.TemporaryDirectory() as tmpdir:
                    pv_parquet_path = os.path.join(tmpdir, "peaks_valleys.parquet")

                    if pulse3d_semver >= "1.0.0":
                        features_df = _create_features_df(
                            details.timepoints, details.peaks_valleys, peak_valley_diff
                        )
                    else:
                        features_df = _create_legacy_features_df(details.peaks_valleys, peak_valley_diff)
                    # write peaks and valleys to parquet file in temporary directory
                    features_df.write_parquet(pv_parquet_path)
                    # upload to s3 under upload id and job id for pulse3d-worker to use
                    upload_file_to_s3(bucket=PULSE3D_UPLOADS_BUCKET, key=key, file=pv_parquet_path)

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


@app.delete("/jobs")
async def soft_delete_jobs(
    request: Request,
    job_ids: list[uuid.UUID] = Query(None),
    token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE)),
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
    if token.account_type == "user" and details.upload_type not in get_product_tags_of_user(token.scopes):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    job_ids = details.job_ids
    # make sure at least one job ID was given
    if not job_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No job IDs given")

    # need to convert UUIDs to str to avoid issues with DB
    job_ids = [str(job_id) for job_id in job_ids]

    bind_context_to_logger({"user_id": token.userid, "customer_id": token.customer_id})

    try:
        async with request.state.pgpool.acquire() as con:
            jobs = await _get_jobs_download(con, token, upload_type=details.upload_type, job_ids=job_ids)

        num_times_repeated = defaultdict(lambda: 0)

        filename_overrides = list()
        keys = list()

        for job in jobs:
            obj_key = job["object_key"]
            keys.append(obj_key)

            filename = os.path.basename(obj_key)

            filename_override = filename
            if details.timezone:
                try:
                    timestamp = job["created_at"]
                    timestamp = timestamp.astimezone(ZoneInfo(details.timezone)).strftime("%Y-%m-%d_%H-%M-%S")
                    filename_override = _add_timestamp_to_filename(obj_key.split("/")[-1], timestamp)
                except Exception:
                    logger.exception(
                        f"Error appending local timestamp download name: {filename=}, timezone={details.timezone} utc_timestamp={job.get('created_at')}"
                    )

            if filename_override in filename_overrides:
                num_times_repeated[filename_override] += 1
                duplicate_num = num_times_repeated[filename_override]
                # add duplicate num to differentiate duplicate filenames
                root, ext = os.path.splitext(filename_override)
                filename_override = f"{root}_({duplicate_num}){ext}"

            filename_overrides.append(filename_override)

        if len(jobs) == 1:
            # if only one file requested, return single presigned URL
            return {
                "id": jobs[0]["id"],
                "url": generate_presigned_url(
                    PULSE3D_UPLOADS_BUCKET, keys[0], filename_override=filename_overrides[0]
                ),
            }
        else:
            # Grab ZIP file from in-memory, make response with correct MIME-type
            return StreamingResponse(
                content=stream_zip(
                    yield_s3_objects(bucket=PULSE3D_UPLOADS_BUCKET, keys=keys, filenames=filename_overrides)
                ),
                media_type="application/zip",
            )

    except Exception:
        logger.exception("Failed to download jobs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _add_timestamp_to_filename(filename: str, timestamp: str) -> str:
    name, ext = os.path.splitext(filename)
    return f"{name}__{timestamp}{ext}"


@app.get("/jobs/waveform-data", response_model=WaveformDataResponse | GenericErrorResponse)
async def get_job_waveform_data(
    request: Request,
    upload_type: str = Query(),
    job_id: uuid.UUID = Query(),
    token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ)),
):
    if job_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required ids to get job metadata."
        )

    job_id = str(job_id)  # type: ignore

    bind_context_to_logger({"customer_id": token.customer_id, "user_id": token.userid, "job_id": job_id})

    try:
        logger.info(f"Getting metadata for job {job_id}")
        async with request.state.pgpool.acquire() as con:
            selected_job = await _get_job_waveform_data(con, token, job_id=job_id, upload_type=upload_type)  # type: ignore

        if not selected_job:
            return GenericErrorResponse(
                message="Job not found or not authorized to run Interactive Analysis on this file",
                error="AuthorizationError",
            )

        parsed_meta = json.loads(selected_job["job_meta"])
        analysis_params = parsed_meta.get("analysis_params", {})
        pulse3d_version = parsed_meta.get("version")

        # Get presigned url for time force data
        pre_analysis_filename = os.path.splitext(selected_job["filename"])[0]
        if pulse3d_version is None:
            pre_analysis_s3_key = f"{selected_job['prefix']}/time_force_data/{pre_analysis_filename}.parquet"
        elif VersionInfo.parse(pulse3d_version.split("rc")[0]) < "1.0.0":
            # TODO remove the split above once we're done with RC versions? Will make IA not work for any jobs run with an rc version, but that might be ok
            pre_analysis_s3_key = (
                f"{selected_job['prefix']}/time_force_data/{pulse3d_version}/{pre_analysis_filename}.parquet"
            )
        else:
            pre_analysis_s3_key = f"{selected_job['prefix']}/{job_id}/pre-analysis.zip"

        logger.info(f"Generating presigned URL for {pre_analysis_s3_key}")
        try:
            time_force_url = generate_presigned_url(PULSE3D_UPLOADS_BUCKET, pre_analysis_s3_key)
        except ValueError:
            message = f"Pre-analysis file was not found in S3 under key {pre_analysis_s3_key}"
            logger.exception(message)
            return GenericErrorResponse(error="MissingDataError", message=message)

        # Get presigned url for peaks and valleys
        logger.info("Generating presigned URL for peaks and valleys")
        pv_parquet_key = f"{selected_job['prefix']}/{job_id}/peaks_valleys.parquet"
        try:
            peaks_valleys_url = generate_presigned_url(PULSE3D_UPLOADS_BUCKET, pv_parquet_key)
        except ValueError:
            message = f"Peaks/Valleys Parquet file was not found in S3 under key {pv_parquet_key}"
            logger.exception(message)
            return GenericErrorResponse(error="MissingDataError", message=message)

        data_type_str: str | None = parsed_meta.get("data_type")
        if data_type_str:
            data_type = DataTypes[data_type_str.upper()]
        else:
            # if data type is not present, is present and is None, or some other falsey value, set to force as default
            data_type = DataTypes.FORCE

        return WaveformDataResponse(
            time_force_url=time_force_url,
            peaks_valleys_url=peaks_valleys_url,
            amplitude_label=get_metric_display_title(
                TwitchMetrics.AMPLITUDE,
                data_type,
                normalization_method=analysis_params.get("normalization_method"),
            ),
        )
    except S3Error:
        logger.exception("Error from s3")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception:
        logger.exception("Failed to get interactive waveform data")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/versions")
async def get_versions(request: Request):
    """Retrieve info of all the active pulse3d releases listed in the DB."""
    try:
        async with request.state.pgpool.acquire() as con:
            rows = await con.fetch(
                "SELECT version, state, end_of_life_date FROM pulse3d_versions "
                "WHERE state != 'deprecated' OR NOW() < end_of_life_date ORDER BY created_at"
            )
        return [dict(row) for row in rows]

    except Exception:
        logger.exception("Failed to retrieve info of pulse3d versions")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/usage", response_model=UsageQuota)
async def get_usage_quota(
    request: Request, service: str = Query(None), token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ))
):
    """Get the usage quota for the specific customer"""
    try:
        customer_id = str(uuid.UUID(token.customer_id))

        bind_context_to_logger({"customer_id": customer_id})

        async with request.state.pgpool.acquire() as con:
            usage_quota = await check_customer_pulse3d_usage(con, customer_id, service)
            return usage_quota
    except Exception:
        logger.exception("Failed to fetch usage quota")
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
            await create_analysis_preset(con, user_id, details)
    except Exception:
        logger.exception("Failed to save analysis preset for user")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/presets")
async def get_analysis_presets(
    request: Request, upload_type: str = Query(), token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE))
):
    """Get analysis parameter preset for user"""
    try:
        user_id = str(uuid.UUID(token.userid))
        customer_id = str(uuid.UUID(token.customer_id))
        bind_context_to_logger({"customer_id": customer_id, "user_id": user_id})

        async with request.state.pgpool.acquire() as con:
            return await con.fetch(
                "SELECT name, parameters FROM analysis_presets WHERE user_id=$1 AND type=$2",
                user_id,
                upload_type,
            )

    except Exception:
        logger.exception("Failed to get analysis presets for user")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.delete("/presets/{preset_name}")
async def delete_analysis_preset(
    request: Request, preset_name: str, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE))
):
    """Delete analysis parameter preset for user"""
    try:
        user_id = str(uuid.UUID(token.userid))
        customer_id = str(uuid.UUID(token.customer_id))
        bind_context_to_logger({"customer_id": customer_id, "user_id": user_id})

        async with request.state.pgpool.acquire() as con:
            await con.execute(
                "DELETE FROM analysis_presets WHERE user_id=$1 AND name=$2", user_id, preset_name
            )

    except Exception:
        logger.exception(f"Failed to delete analysis preset {preset_name} for user")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/notification_messages", response_model=list[NotificationMessageResponse])
async def get_notification_messages(
    notification_message_id: uuid.UUID = Query(None), token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_READ))
):
    """Get info for user|customer notification messages."""
    try:
        account_id = str(uuid.UUID(token.account_id))
        nm_id = str(notification_message_id) if notification_message_id else None
        bind_context_to_logger({"account_id": account_id})
        response = await notification_service.get_notification_messages(account_id, nm_id)  # noqa: F821
        return response
    except Exception:
        logger.exception("Failed to get notification messages")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/notification_messages", response_model=ViewNotificationMessageResponse)
async def view_notification_message(
    view_request: ViewNotificationMessageRequest, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE))
):
    """Mark user|customer notification messages as viewed."""
    try:
        account_id = str(uuid.UUID(token.account_id))
        nm_id = str(view_request.id)
        bind_context_to_logger({"account_id": account_id})
        response = await notification_service.view_notification_message(account_id, nm_id)  # noqa: F821
        return response
    except Exception:
        logger.exception("Failed to mark notification message as viewed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/notifications", response_model=list[NotificationResponse])
async def get_all_notifications(token=Depends(ProtectedAny(scopes=[Scopes.CURI__ADMIN]))):
    """Get info for all notifications."""
    try:
        customer_id = str(uuid.UUID(token.customer_id))
        bind_context_to_logger({"customer_id": customer_id})
        response = await notification_service.get_all()  # noqa: F821
        return response
    except Exception:
        logger.exception("Failed to get all notifications")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/notifications", response_model=SaveNotificationResponse, status_code=status.HTTP_201_CREATED)
async def save_notification(
    notification: SaveNotificationRequest, token=Depends(ProtectedAny(scopes=[Scopes.CURI__ADMIN]))
):
    """Save notification"""
    try:
        customer_id = str(uuid.UUID(token.customer_id))
        bind_context_to_logger({"customer_id": customer_id})
        response = await notification_service.create(notification)  # noqa: F821
        return response
    except Exception:
        logger.exception("Failed to save notification")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# HELPERS


def _get_retrieval_info(token, upload_type: str | None):
    account_type = token.account_type
    customer_id = str(uuid.UUID(token.customer_id))
    if token.account_type == "user":
        user_id = str(uuid.UUID(token.userid))
        if upload_type in get_product_tags_of_user(token.scopes, rw_all_only=True):
            account_type = "rw_all_data_user"
    else:
        user_id = None

    return {"user_id": user_id, "customer_id": customer_id, "account_type": account_type}


async def _get_uploads(con, token, **retrieval_info):
    retrieval_info |= _get_retrieval_info(token, retrieval_info["upload_type"])

    upload_type_msg = "" if not retrieval_info["upload_type"] else f"{retrieval_info['upload_type']} "
    logger.info(
        f"Retrieving {upload_type_msg}uploads for {retrieval_info['account_type']}: {token.account_id}"
    )

    match retrieval_info.pop("account_type"):
        case "user":
            return await get_uploads_info_for_base_user(con, **retrieval_info)
        case "rw_all_data_user":
            return await get_uploads_info_for_rw_all_data_user(con, **retrieval_info)
        case "admin":
            return await get_uploads_info_for_admin(con, **retrieval_info)


async def _get_uploads_download(
    con, token, upload_ids: list[str], upload_type: str | None
) -> list[dict[str, Any]]:  # type: ignore
    retrieval_info = _get_retrieval_info(token, upload_type)

    upload_type_msg = "" if not upload_type else f"{upload_type} "
    logger.info(
        f"Downloading {upload_type_msg}uploads for {retrieval_info['account_type']}: {token.account_id}"
    )

    match retrieval_info.pop("account_type"):
        case "user":
            return await get_uploads_download_info_for_base_user(
                con, user_id=retrieval_info["user_id"], upload_type=upload_type, upload_ids=upload_ids
            )
        case "rw_all_data_user":
            return await get_uploads_download_info_for_rw_all_data_user(
                con, customer_id=retrieval_info["customer_id"], upload_type=upload_type, upload_ids=upload_ids
            )
        case "admin":
            return await get_uploads_download_info_for_admin(
                con, customer_id=retrieval_info["customer_id"], upload_ids=upload_ids
            )


async def _get_jobs_of_uploads(con, token, upload_ids: list[str], upload_type: str | None):
    retrieval_info = _get_retrieval_info(token, upload_type)

    logger.info(f"Retrieving jobs of uploads for {retrieval_info['account_type']}: {token.account_id}")

    match retrieval_info.pop("account_type"):
        case "user":
            return await get_jobs_of_uploads_for_base_user(
                con, user_id=retrieval_info["user_id"], upload_type=upload_type, upload_ids=upload_ids
            )
        case "rw_all_data_user":
            return await get_jobs_of_uploads_for_rw_all_data_user(
                con, customer_id=retrieval_info["customer_id"], upload_type=upload_type, upload_ids=upload_ids
            )
        case "admin":
            return await get_jobs_of_uploads_for_admin(
                con, customer_id=retrieval_info["customer_id"], upload_ids=upload_ids
            )


async def _get_legacy_jobs_info(con, token, job_ids: list[str]):
    retrieval_info = _get_retrieval_info(token, upload_type=None)

    logger.info(f"Retrieving legacy job info for {retrieval_info['account_type']}: {token.account_id}")

    match retrieval_info.pop("account_type"):
        case "user" | "rw_all_data_user":
            return await get_legacy_jobs_info_for_user(
                con, user_id=retrieval_info["user_id"], job_ids=job_ids
            )
        case _:
            return []


async def _get_jobs_info(con, token, **retrieval_info):
    retrieval_info |= _get_retrieval_info(token, retrieval_info["upload_type"])

    logger.info(f"Retrieving jobs info for {retrieval_info['account_type']}: {token.account_id}")

    match retrieval_info.pop("account_type"):
        case "user":
            return await get_jobs_info_for_base_user(con, **retrieval_info)
        case "rw_all_data_user":
            return await get_jobs_info_for_rw_all_data_user(con, **retrieval_info)
        case "admin":
            return await get_jobs_info_for_admin(con, **retrieval_info)


async def _get_jobs_download(con, token, job_ids: list[str], upload_type: str | None) -> list[dict[str, Any]]:  # type: ignore
    retrieval_info = _get_retrieval_info(token, upload_type)

    logger.info(f"Downloading job IDs: {job_ids} for {retrieval_info['account_type']}: {token.account_id}")

    match retrieval_info.pop("account_type"):
        case "user":
            return await get_jobs_download_info_for_base_user(
                con, user_id=retrieval_info["user_id"], upload_type=upload_type, job_ids=job_ids
            )
        case "rw_all_data_user":
            return await get_jobs_download_info_for_rw_all_data_user(
                con, customer_id=retrieval_info["customer_id"], upload_type=upload_type, job_ids=job_ids
            )
        case "admin":
            return await get_jobs_download_info_for_admin(
                con, customer_id=retrieval_info["customer_id"], job_ids=job_ids
            )


async def _get_job_waveform_data(con, token, job_id: str, upload_type: str) -> dict[str, Any] | None:  # type: ignore
    retrieval_info = _get_retrieval_info(token, upload_type)

    logger.info(
        f"Retrieving waveform data of job: {job_id} for {retrieval_info['account_type']}: {token.account_id}"
    )

    match retrieval_info.pop("account_type"):
        case "user":
            return await get_job_waveform_data_for_base_user(
                con, user_id=retrieval_info["user_id"], upload_type=upload_type, job_id=job_id
            )
        case "rw_all_data_user":
            return await get_job_waveform_data_for_rw_all_data_user(
                con, customer_id=retrieval_info["customer_id"], upload_type=upload_type, job_id=job_id
            )
        case "admin":
            return await get_job_waveform_data_for_admin_user(
                con, customer_id=retrieval_info["customer_id"], job_id=job_id
            )


def _generate_presigned_post(details, bucket, s3_key):
    s3_key += f"/{details.filename}"
    logger.info(f"Generating presigned upload url for {bucket}/{s3_key}")
    params = generate_presigned_post(bucket=bucket, key=s3_key, md5s=details.md5s)
    return params


def _create_features_df(timepoints, features, peak_valley_diff):
    ia_features = _create_legacy_features_df(features, peak_valley_diff)

    wells = {c.split("__")[0] for c in ia_features.select(pl.exclude("time")).columns}

    formatted_features = create_empty_df(timepoints, wells)

    for well in wells:
        peaks = ia_features[f"{well}__peaks"].cast(int).drop_nulls()
        valleys = ia_features[f"{well}__valleys"].cast(int).drop_nulls()

        formatted_features = mark_features(formatted_features, peaks, FeatureMarkers.PEAK, well)
        formatted_features = mark_features(formatted_features, valleys, FeatureMarkers.VALLEY, well)

    return formatted_features


def _create_legacy_features_df(features, peak_valley_diff):
    df = pl.DataFrame()

    # format peaks and valleys to simple df
    for well, peaks_valleys in features.items():
        for feature_idx, feature_name in enumerate(["peaks", "valleys"]):
            well_idxs_of_feature = (
                pl.DataFrame({f"{well}__{feature_name}": peaks_valleys[feature_idx]}) + peak_valley_diff
            )
            df = pl.concat([df, well_idxs_of_feature], how="horizontal")

    return df


def _format_tuple_param(
    options: TupleParam | None,
    default_values: int | float | tuple[int, ...] | tuple[float, ...],
    allow_float=True,
) -> TupleParam | None:
    if options is None or all(op is None for op in options):
        return None

    if isinstance(default_values, (int, float)):
        default_values = (default_values,) * len(options)

    def get_val(num: int | float | None, default_value: int | float) -> int | float:
        if num is None:
            return default_value
        if allow_float:
            return num
        return int(num)

    # set any unspecified values to the default value
    formatted_options = tuple(
        get_val(option, default_value) for option, default_value in zip(options, default_values)
    )

    return formatted_options
