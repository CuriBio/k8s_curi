from codecs import unicode_escape_decode
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from fastapi import FastAPI, Request, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from auth import ProtectedAny
from core.config import DATABASE_URL, PULSE3D_UPLOADS_BUCKET, MANTARRAY_LOGS_BUCKET
from jobs import create_upload, create_job, get_uploads, get_jobs
from utils.db import AsyncpgPoolDep
from utils.s3 import generate_presigned_post, generate_presigned_url, S3Error


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


class JobRequest(BaseModel):
    upload_id: uuid.UUID
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
    # need to convert to UUIDs to str to avoid issues with DB
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


# TODO Tanner (4/21/22): probably want to move this to a more general svc (maybe in apiv2-dep) dedicated to uploading misc files to s3
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
                    job_info["error_info"] = json.loads(job["job_meta"])["error"]

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
    print("here")
    try:
        user_id = str(uuid.UUID(token["userid"]))
        logger.info(f"Creating pulse3d job for upload {details.upload_id} with user ID: {user_id}")

        meta = {
            "analysis_params": {
                param: dict(details)[param]
                for param in (
                    "prominence_factors",
                    "width_factors",
                    "twitch_widths",
                    "start_time",
                    "end_time",
                )
            }
        }

        # convert FE output to pulse3dInput
        # done for width and prominece factors
        meta["analysis_params"]["prominence_factors"] = _format_advanced_options(
            meta["analysis_params"]["prominence_factors"]
        )
        meta["analysis_params"]["width_factors"] = _format_advanced_options(
            meta["analysis_params"]["width_factors"]
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


def _format_advanced_options(option: List[Union[int, float, None]]):
    if option is None:
        return None
    # if only peaks is passed return tupele(peaks,)
    if option[0] is not None and option[1] is None:
        return (option[0],)
    # if only valleys is passed return (None,valleys)
    if option[0] is None and option[1] is not None:
        return (None, option[1])
    # if both present then return a tuple
    return (option[0], option[1])
