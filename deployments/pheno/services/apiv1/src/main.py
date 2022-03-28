from fastapi import FastAPI, APIRouter, Request, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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


@app.on_event("startup")
async def startup():
    await db.create_pool()


@app.on_event("shutdown")
async def shutdown():
    await db.close()


@app.middleware("http")
async def catch_exceptions(request: Request, call_next):
    return await call_next(request)


@app.exception_handler(RequestValidationError)  # can evenstually add handling to remove sensitive data
async def validation_exception_handler(request, err):
    base_error_message = f"Failed to execute: {request.method}: {request.url}"
    return JSONResponse(status_code=400, content=f"{base_error_message}: {err.errors()[0]}")
