import os
import logging
import json
import uuid

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import ProtectedAny
from jobs import create_upload, create_job, get_uploads, get_jobs
from utils.s3 import generate_presigned_post
from utils.db import AsyncpgPoolDep
from core.config import DATABASE_URL, PULSE3D_UPLOADS_BUCKET


logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

app = FastAPI()
asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)


class UploadRequest(BaseModel):
    filename: str
    md5s: str
    customer_id: str


class JobRequest(BaseModel):
    upload_id: str


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.pgpool = await asyncpg_pool()
    response = await call_next(request)
    return response


@app.on_event("startup")
async def startup():
    await asyncpg_pool()


@app.get("/uploads")
async def get_all_uploads(request: Request, token=Depends(ProtectedAny(scope=["users:free"]))):
    try:
        user_id = str(uuid.UUID(token["userid"]))
        async with request.state.pgpool.acquire() as con:
            return await get_uploads(con=con, user_id=user_id)
    except Exception as e:
        logger.exception("Failed to get uploads")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/uploads/{upload_id}")
async def get_upload_route(
    request: Request, upload_id: str, token=Depends(ProtectedAny(scope=["users:free"]))
):
    try:
        user_id = str(uuid.UUID(token["userid"]))
        async with request.state.pgpool.acquire() as con:
            return await get_uploads(con=con, user_id=user_id, upload_id=upload_id)
    except Exception as e:
        logger.exception("Failed to get uploads")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/uploads")
async def create_upload_route(
    request: Request, details: UploadRequest, token=Depends(ProtectedAny(scope=["users:free"]))
):
    try:
        user_id = str(uuid.UUID(token["userid"]))
        key = f"uploads/{details.customer_id}/{user_id}/{details.filename}"

        logger.info(
            f"Generating presigned upload url for {PULSE3D_UPLOADS_BUCKET}/uploads/{details.customer_id}/{user_id}/{details.filename}"
        )
        params = generate_presigned_post(bucket=PULSE3D_UPLOADS_BUCKET, key=key, md5s=details.md5s)

        # TODO what meta do we want
        meta = {
            "prefix": f"uploads/{details.customer_id}/{user_id}",
            "filename": details.filename,
            "md5s": details.md5s,
        }

        async with request.state.pgpool.acquire() as con:
            upload_id = await create_upload(con=con, user_id=user_id, meta=meta)

            # TODO define a response model for uploads
            return {"id": upload_id, "params": params}
    except Exception as e:
        logger.exception("Failed to generate presigned upload url")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)


@app.get("/jobs")
async def get_all_users_jobs(request: Request, token=Depends(ProtectedAny(scope=["users:free"]))):
    try:
        user_id = str(uuid.UUID(token["userid"]))
        logger.info(f"GET /jobs for user: {user_id}")

        async with request.state.pgpool.acquire() as con:
            return await get_jobs(con=con, user_id=user_id)

    except Exception as e:
        logger.exception("Failed to create job")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/jobs")
async def create_job_route(
    request: Request, details: JobRequest, token=Depends(ProtectedAny(scope=["users:free"]))
):
    try:
        user_id = str(uuid.UUID(token["userid"]))
        logger.info(f"Creating pulse3d job for upload {details.upload_id} with user: {user_id}")

        # TODO what meta do we want?
        meta = {}

        # TODO check upload_id is valid
        async with request.state.pgpool.acquire() as con:
            job_id = await create_job(
                con=con, upload_id=details.upload_id, queue="pulse3d", priority=10, meta=meta
            )
            return {
                "id": job_id,
                "user_id": user_id,
                "upload_id": details.upload_id,
                "status": "pending",
                "priority": 10,
            }

    except Exception as e:
        logger.exception("Failed to create job")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
