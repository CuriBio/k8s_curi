import os
import logging
import uuid

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import ProtectedAny
from utils.s3 import generate_presigned_post
from utils.db import AsyncpgPoolDep
from core.config import DATABASE_URL, PULSE3D_UPLOADS_BUCKET


logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

app = FastAPI()
asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)


class Uploads(BaseModel):
    filename: str
    md5s: str


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.pgpool = await asyncpg_pool()
    response = await call_next(request)
    return response


@app.on_event("startup")
async def startup():
    await asyncpg_pool()


@app.post("/uploads")
async def create_upload(request: Request, details: Uploads, token=Depends(ProtectedAny(scope=["users:free"]))):
    try:
        user_id = str(uuid.UUID(token["userid"]))
        logger.info(f"Generating presigned upload url for {PULSE3D_UPLOADS_BUCKET}/{user_id}/{details.filename}")
        params = generate_presigned_post(bucket=PULSE3D_UPLOADS_BUCKET, key=f"{user_id}/{details.filename}", md5s=details.md5s)

        #TODO add upload to uploads table

        return params
    except Exception as e:
        logger.exception("Failed to generate presigned upload url")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

