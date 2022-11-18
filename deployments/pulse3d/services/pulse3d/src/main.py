from collections import defaultdict
import json
import logging
from typing import List, Optional, Tuple, Union
import uuid
import tempfile
import boto3
import os
import numpy as np
import pandas as pd
from glob import glob
from semver import VersionInfo

from stream_zip import ZIP_64, stream_zip
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pulse3D.peak_detection import peak_detector
from pulse3D.constants import (
    MICRO_TO_BASE_CONVERSION,
    DEFAULT_BASELINE_WIDTHS,
    DEFAULT_PROMINENCE_FACTORS,
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
    UsageErrorResponse,
    UploadDownloadRequest,
)
from models.types import TupleParam

from utils.db import AsyncpgPoolDep
from utils.s3 import generate_presigned_post, generate_presigned_url, S3Error, download_directory_from_s3


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
        async with request.state.pgpool.acquire() as con:
            return await get_uploads(
                con=con, account_type=token["account_type"], account_id=account_id, upload_ids=upload_ids
            )

    except Exception as e:
        logger.exception(f"Failed to get uploads: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/uploads", response_model=Union[UploadResponse, UsageErrorResponse])
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
                return UsageErrorResponse(usage_error=usage_quota)

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
    user_id = str(uuid.UUID(token["userid"]))

    try:
        async with request.state.pgpool.acquire() as con:
            uploads = await get_uploads(
                con=con, account_type=token["account_type"], account_id=user_id, upload_ids=upload_ids
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
        service, _ = split_scope_account_data(token["scope"][0])
        logger.info(f"Creating {service} job for upload {details.upload_id} with user ID: {user_id}")

        params = [
            "baseline_widths_to_use",
            "prominence_factors",
            "width_factors",
            "twitch_widths",
            "start_time",
            "end_time",
        ]

        # don't add params unless the selected pulse3d version supports it
        pulse3d_semver = VersionInfo.parse(details.version)
        if pulse3d_semver >= "0.25.0":
            params.append("max_y")
        if pulse3d_semver >= "0.25.2":
            params.append("peaks_valleys")
        if pulse3d_semver >= "0.25.4":
            params.append("normalize_y_axis")
        if pulse3d_semver >= "0.26.0":
            params.append("stiffness_factor")
        if pulse3d_semver >= "0.27.4":
            params.append("inverted_post_magnet_wells")
        if pulse3d_semver >= "0.28.1":
            params.append("include_stim_protocols")

        details_dict = dict(details)
        analysis_params = {param: details_dict[param] for param in params}

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
            usage_quota = await check_customer_quota(con, customer_id, service)
            if usage_quota["jobs_reached"]:
                return UsageErrorResponse(usage_error=usage_quota)

            job_id = await create_job(
                con=con,
                upload_id=details.upload_id,
                queue=f"pulse3d-v{details.version}",
                priority=priority,
                meta={"analysis_params": analysis_params, "version": details.version},
                customer_id=customer_id,
                job_type=service,
            )

        return JobResponse(
            id=job_id, user_id=user_id, upload_id=details.upload_id, status="pending", priority=priority
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


@app.get("/jobs/waveform_data", response_model=WaveformDataResponse)
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required ids to get job metadata.",
        )

    upload_id = str(upload_id)
    job_id = str(job_id)

    # grab jobs meta data to use in peak_detector if necessary
    # TODO remove this step when peaks and valleys get saved to parquet on initial analysis
    try:
        async with request.state.pgpool.acquire() as con:
            logger.info(f"Getting metadata for job {job_id}")
            jobs = await _get_jobs(con, token, [job_id])

        parsed_meta = json.loads(jobs[0]["job_meta"])
        analysis_params = parsed_meta["analysis_params"]

        with tempfile.TemporaryDirectory() as tmpdir:
            key = f"uploads/{customer_id}/{account_id}/{upload_id}"
            logger.info(f"Downloading recording data from {key}")

            download_directory_from_s3(bucket=PULSE3D_UPLOADS_BUCKET, key=key, file_path=tmpdir)

            # read the time force dataframe from the parquet file
            # older versions of pulse3d do not inlcude the version data
            if pulse3d_version := parsed_meta.get("version"):
                parquet_path = glob(
                    os.path.join(tmpdir, "time_force_data", pulse3d_version, "*.parquet"),
                    recursive=True,
                )
            else:
                parquet_path = glob(os.path.join(tmpdir, "time_force_data", "*.parquet"), recursive=True)

            df = pd.read_parquet(parquet_path)

            # remove raw data columns
            columns = [c for c in df.columns if "__raw" not in c]
            # this is to handle analyses run before PR.to_dataframe() where time is in seconds
            needs_unit_conversion = not [c for c in df.columns if "__raw" in c]

            time = df["Time (s)"].tolist()
            if needs_unit_conversion:
                logger.info("Old parquet file found so converting time column to microseconds")
                # needs to be us for peak_detector
                time = [i * MICRO_TO_BASE_CONVERSION for i in time]

            # set up empty dictionaries to be passed in response
            coordinates = dict()
            # old jobs won't have this param yet and it will default to None on first analysis
            peaks_valleys_needed = (
                "peaks_valleys" not in analysis_params or analysis_params["peaks_valleys"] is None
            )
            peaks_and_valleys = analysis_params["peaks_valleys"] if not peaks_valleys_needed else dict()

            for well in columns[1:]:
                logger.info(f"Finding peaks and valleys for well at {well}")

                well_force = df[well]
                if needs_unit_conversion:
                    # not exact, but this isn't used outside of graphing in FE, real raw data doesn't get changed
                    min_value = min(well_force)
                    well_force -= min_value
                    well_force *= MICRO_TO_BASE_CONVERSION

                interpolated_well_data = np.row_stack([time, well_force])

                if peaks_valleys_needed:
                    # TODO remove once peaks and valleys get stored in parquet files
                    peak_detector_params = {
                        param: analysis_params[param]
                        for param in (
                            "prominence_factors",
                            "width_factors",
                            "start_time",
                            "end_time",
                        )
                        if analysis_params[param] is not None
                    }
                    peaks, valleys = peak_detector(interpolated_well_data, **peak_detector_params)
                    # needs to be converted to lists to be sent as json in response
                    peaks_and_valleys[well] = [peaks.tolist(), valleys.tolist()]

                well_coords = [
                    [time[i] / MICRO_TO_BASE_CONVERSION, val] for (i, val) in enumerate(well_force)
                ]
                coordinates[well] = well_coords

            return WaveformDataResponse(coordinates=coordinates, peaks_valleys=peaks_and_valleys)

    except KeyError:
        logger.error("Job metadata was not returned from database.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except S3Error as e:
        logger.error(f"Error from s3: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Failed to get interactive waveform data: {e}")
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
