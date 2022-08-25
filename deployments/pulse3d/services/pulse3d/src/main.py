import json
from lib2to3.pytree import Base
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid
import tempfile
import os
from zipfile import ZipFile
from datetime import datetime
import io

from fastapi import FastAPI, Request, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from auth import ProtectedAny
from core.config import DATABASE_URL, PULSE3D_UPLOADS_BUCKET, MANTARRAY_LOGS_BUCKET
from jobs import create_upload, create_job, get_uploads, get_jobs, delete_jobs, delete_uploads
from utils.db import AsyncpgPoolDep
from utils.s3 import generate_presigned_post, generate_presigned_url, S3Error, download_file_from_s3


logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

app = FastAPI(openapi_url=None)
asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)


class UploadRequest(BaseModel):
    filename: str
    md5s: Optional[str]
    upload_type: str


class UploadResponse(BaseModel):
    id: uuid.UUID
    params: Dict[str, Any]


class DownloadItem(BaseModel):
    jobId: uuid.UUID
    uploadId: uuid.UUID
    analyzedFile: str
    datetime: str
    status: str
    analysisParams: Dict[Any, Any]


class DownloadRequest(BaseModel):
    jobs: List[DownloadItem]


class JobRequest(BaseModel):
    upload_id: uuid.UUID
    max_y: Optional[Union[int, float]]
    prominence_factors: Optional[Tuple[Union[int, float, None], Union[int, float, None]]]
    width_factors: Optional[Tuple[Union[int, float, None], Union[int, float, None]]]
    twitch_widths: Optional[List[int]]
    start_time: Optional[Union[int, float]]
    end_time: Optional[Union[int, float]]


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dashboard.curibio-test.com",
        "https://dashboard.curibio.com",
        "http://localhost:3000",
    ],
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
    token=Depends(ProtectedAny(scope=["users:free"])),
):
    # need to convert to UUIDs to str to avoid issues with Db
    if upload_ids:
        upload_ids = [str(upload_id) for upload_id in upload_ids]

    try:
        user_id = str(uuid.UUID(token["userid"]))
        async with request.state.pgpool.acquire() as con:
            return await get_uploads(con=con, user_id=user_id, upload_ids=upload_ids)

    except Exception as e:
        logger.exception(f"Failed to get uploads: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/uploads", response_model=UploadResponse)
async def create_recording_upload(
    request: Request,
    details: UploadRequest,
    token=Depends(ProtectedAny(scope=["users:free"])),
):
    try:
        user_id = str(uuid.UUID(token["userid"]))
        customer_id = str(uuid.UUID(token["customer_id"]))

        upload_params = {
            "prefix": f"uploads/{customer_id}/{user_id}/{{upload_id}}",
            "filename": details.filename,
            "md5": details.md5s,
            "user_id": user_id,
            "type": details.upload_type,
        }
        async with request.state.pgpool.acquire() as con:
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
    token=Depends(ProtectedAny(scope=["users:free"])),
):
    # check if for some reason an empty list was sent
    if not upload_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No upload ids found.",
        )
    # need to convert UUIDs to str to avoid issues with DB
    upload_ids = [str(upload_id) for upload_id in upload_ids]

    try:
        async with request.state.pgpool.acquire() as con:
            await delete_uploads(con=con, upload_ids=upload_ids)
    except Exception as e:
        logger.error(repr(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# TODO Tanner (4/21/22): probably want to move this to a more general svc (maybe in apiv2-dep) dedicated to uploading misc files to s3.
@app.post("/logs")
async def create_log_upload(
    request: Request,
    details: UploadRequest,
    token=Depends(ProtectedAny(scope=["users:free"])),
):
    try:
        user_id = str(uuid.UUID(token["userid"]))
        customer_id = str(uuid.UUID(token["customer_id"]))
        params = _generate_presigned_post(user_id, customer_id, details, MANTARRAY_LOGS_BUCKET)
        # TODO define a response model for logs
        return {"params": params}
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
    token=Depends(ProtectedAny(scope=["users:free"])),
):
    # need to convert UUIDs to str to avoid issues with DB
    if job_ids:
        job_ids = [str(job_id) for job_id in job_ids]

    try:
        user_id = str(uuid.UUID(token["userid"]))
        logger.info(f"Retrieving job info with IDs: {job_ids} for user: {user_id}")

        async with request.state.pgpool.acquire() as con:
            jobs = await get_jobs(con=con, user_id=user_id, job_ids=job_ids)
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


@app.post("/jobs")
async def create_new_job(
    request: Request,
    details: JobRequest,
    token=Depends(ProtectedAny(scope=["users:free"])),
):
    try:
        user_id = str(uuid.UUID(token["userid"]))
        logger.info(f"Creating pulse3d job for upload {details.upload_id} with user ID: {user_id}")

        meta = {
            "analysis_params": {
                param: dict(details)[param]
                for param in (
                    "max_y",
                    "prominence_factors",
                    "width_factors",
                    "twitch_widths",
                    "start_time",
                    "end_time",
                )
            }
        }

        # convert FE output to pulse3d input
        # done for width and prominece factors
        meta["analysis_params"]["prominence_factors"] = _format_advanced_options(
            meta["analysis_params"]["prominence_factors"], "prominence"
        )
        meta["analysis_params"]["width_factors"] = _format_advanced_options(
            meta["analysis_params"]["width_factors"], "width"
        )
        logger.info(f"Using params: {meta['analysis_params']}")

        async with request.state.pgpool.acquire() as con:
            priority = 10
            job_id = await create_job(
                con=con,
                upload_id=details.upload_id,
                queue="pulse3d",
                priority=priority,
                meta=meta,
            )

            # TODO create response model
            return {
                "id": job_id,
                "user_id": user_id,
                "upload_id": details.upload_id,
                "status": "pending",
                "priority": priority,
            }

    except Exception as e:
        logger.exception(f"Failed to create job: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _format_advanced_options(option: List[Union[int, float, None]], option_name):
    if option is None:
        return None
    # if only peaks is passed return tuple(peaks,default value)
    if option[0] is not None and option[1] is None:
        if option_name == "width":
            return option[0], 7
        if option_name == "prominence":
            return option[0], 6
    # if only valleys is passed return (default value,valleys)
    if option[0] is None and option[1] is not None:
        if option_name == "width":
            return 7, option[1]
        if option_name == "prominence":
            return 6, option[1]
    # if both present then return a tuple
    return option[0], option[1]


@app.delete("/jobs")
async def soft_delete_jobs(
    request: Request,
    job_ids: List[uuid.UUID] = Query(None),
    token=Depends(ProtectedAny(scope=["users:free"])),
):
    # check if for some reason an empty list was sent
    if not job_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No job ids found.",
        )
    # need to convert UUIDs to str to avoid issues with DB
    job_ids = [str(job_id) for job_id in job_ids]

    try:
        async with request.state.pgpool.acquire() as con:
            await delete_jobs(con=con, job_ids=job_ids)
    except Exception as e:
        logger.error(f"Failed to soft delete jobs: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/download")
async def download_analyses(
    request: Request,
    details: DownloadRequest,
    token=Depends(ProtectedAny(scope=["users:free"])),
):

    jobs = details.jobs

    # check if for some reason an empty list was sent
    if not jobs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nothing to download.",
        )

    user_id = str(uuid.UUID(token["userid"]))
    customer_id = str(uuid.UUID(token["customer_id"]))
    num_of_files = len(jobs)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            now = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            zip_filename = f"MA-analyses__{now}__{num_of_files}.zip"
            zip_filepath = os.path.join(tmpdir, zip_filename)

            with ZipFile(zip_filepath, "w") as zip_file:
                for job in jobs:
                    upload_id = job.uploadId
                    job_id = job.jobId
                    filename = job.analyzedFile

                    try:
                        file_path = os.path.join(tmpdir, filename)
                        if os.path.exists(file_path):
                            # grabs index of file in list of duplicate filenames to append to filename to differentiate
                            duplicate_filename = [j.jobId for j in jobs if j.analyzedFile == filename]
                            idx = duplicate_filename.index(job_id)
                            # add duplicate index to differentiate duplicate filenames
                            root, ext = os.path.splitext(file_path)
                            file_path = "".join([f"{root}_({idx})", ext])

                        key_prefix = f"analyzed/{customer_id}/{user_id}/{upload_id}/{job_id}/{filename}"
                        download_file_from_s3(
                            bucket=PULSE3D_UPLOADS_BUCKET, key=key_prefix, file_path=file_path
                        )
                    except Exception as e:
                        logger.error(e)
                        continue  # continue loop if one file fails, download function logs error itself
                    else:
                        logger.info(f"Writing {filename} to zip.")
                        zip_file.write(file_path, os.path.basename(file_path))

           
                # Grab ZIP file from in-memory, make response with correct MIME-type
                return FileResponse(path=zip_filepath, filename=zip_filename)

    except Exception as e:
        logger.error(f"Failed to download analyses: {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
