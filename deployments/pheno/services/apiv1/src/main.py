from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.exceptions import RequestValidationError

from lib.models import *
from lib.db import database as db
from endpoints import segmentations
from endpoints import segtrainings
from endpoints import trainings
from endpoints import classifications
from endpoints import dashboard
from endpoints import user

app = FastAPI()
api_router = APIRouter()

api_router.include_router(trainings.router)
api_router.include_router(user.router)
api_router.include_router(dashboard.router)
api_router.include_router(segmentations.router)
api_router.include_router(segtrainings.router)
api_router.include_router(classifications.router)

app.include_router(api_router)


@app.exception_handler(RequestValidationError)  # can eventually add handling to remove sensitive data
async def validation_exception_handler(request, err):
    base_error_message = f"Failed to execute: {request.method}: {request.url}"
    raise HTTPException(status_code=400, detail=f"{base_error_message}: {err.errors()[0]}")


@app.on_event("startup")
async def startup():
    await db.create_pool()


@app.on_event("shutdown")
async def shutdown():
    await db.close()


@app.middleware("http")
async def pre_post_request(request: Request, call_next):
    # pre-request
    response = await call_next(request)
    # post-request
    return response
