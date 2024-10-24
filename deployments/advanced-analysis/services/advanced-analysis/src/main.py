from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
import os
import time
from typing import Any
import uuid
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Response, Depends, status, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette_context import context, request_cycle_context
from stream_zip import stream_zip
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from uvicorn.protocols.utils import get_path_with_query_string

from auth import ProtectedAny, ScopeTags, get_product_tags_of_user
from jobs import (
    check_customer_advanced_analysis_usage,
    create_advanced_analysis_job,
    delete_advanced_analyses,
    get_advanced_analyses_for_admin,
    get_advanced_analyses_for_base_user,
    get_advanced_analyses_download_info_for_base_user,
    get_advanced_analyses_download_info_for_admin,
)
from utils.db import AsyncpgPoolDep
from utils.logging import setup_logger, bind_context_to_logger
from utils.s3 import yield_s3_objects, generate_presigned_url
from core.config import DATABASE_URL, DASHBOARD_URL, PULSE3D_UPLOADS_BUCKET
from models.models import (
    GetAdvancedAnalysesResponse,
    GetAdvancedAnalysisUsageResponse,
    PostAdvancedAnalysesRequest,
    PostAdvancedAnalysesDownloadRequest,
)

setup_logger()
logger = structlog.stdlib.get_logger("api.access")

asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncpg_pool()
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
async def middleware(request: Request, call_next) -> Response:
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


# ROUTES


@app.get("/versions")
async def get_versions(request: Request):
    """Retrieve info of all the active advanced analysis releases listed in the DB."""
    try:
        async with request.state.pgpool.acquire() as con:
            rows = await con.fetch(
                "SELECT version, state, end_of_life_date FROM advanced_analysis_versions "
                "WHERE state != 'deprecated' OR NOW() < end_of_life_date ORDER BY created_at"
            )
        return [dict(row) for row in rows]

    except Exception:
        logger.exception("Failed to retrieve info of advanced analysis versions")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/usage", response_model=GetAdvancedAnalysisUsageResponse)
async def get_usage(request: Request, token=Depends(ProtectedAny(tag=ScopeTags.ADVANCED_ANALYSIS_READ))):
    """Get the current usage and usage limit for the specific customer"""
    try:
        customer_id = str(uuid.UUID(token.customer_id))
        bind_context_to_logger({"customer_id": customer_id})

        async with request.state.pgpool.acquire() as con:
            return await check_customer_advanced_analysis_usage(con, customer_id)
    except Exception:
        logger.exception("Failed to fetch usage quota")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/advanced-analyses", response_model=GetAdvancedAnalysesResponse)
async def get_advanced_analyses(
    request: Request,
    sort_field: str | None = Query(None),
    sort_direction: str | None = Query(None),
    skip: int = Query(0),
    limit: int = Query(300),
    token=Depends(ProtectedAny(tag=ScopeTags.ADVANCED_ANALYSIS_READ)),
):
    try:
        bind_context_to_logger({"user_id": token.userid, "customer_id": token.customer_id})

        filters = {
            filter_name: filter_value
            for filter_name in ("name", "id", "created_at_min", "created_at_max", "type")
            if (filter_value := request.query_params.get(filter_name))
        }

        async with request.state.pgpool.acquire() as con:
            return await _get_advanced_analyses_info(
                con,
                token,
                sort_field=sort_field,
                sort_direction=sort_direction,
                skip=skip,
                limit=limit,
                **filters,
            )
    except Exception:
        logger.exception("Failed to get advanced analyses")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/advanced-analyses", status_code=status.HTTP_201_CREATED)
async def create_new_advanced_analysis(
    request: Request,
    details: PostAdvancedAnalysesRequest,
    token=Depends(ProtectedAny(tag=ScopeTags.ADVANCED_ANALYSIS_WRITE)),
):
    try:
        user_id = str(uuid.UUID(token.userid))
        customer_id = str(uuid.UUID(token.customer_id))
        sources = details.sources

        bind_context_to_logger({"user_id": user_id, "customer_id": customer_id})

        logger.info(f"Creating job with sources {sources} for user ID: {user_id}")
        logger.info(f"Details: {details.model_dump_json()}")

        params = ["experiment_start_time_utc", "local_tz_offset_hours"]
        details_dict = details.model_dump()
        analysis_params: dict[str, Any] = {param: details_dict[param] for param in params} | {
            "experiment_start_time_utc": details_dict["experiment_start_time_utc"].strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }
        job_meta = {
            "version": details.version + "rc7",  # TODO remove this once done with rc versions,
            "output_name": details.output_name,
            "platemap_overrides": details.platemap_overrides,
            "analysis_params": analysis_params,
        }
        queue = f"advanced-analysis-v{job_meta['version']}"

        priority = 10  # TODO make this a constant and share with p3d svc?
        async with request.state.pgpool.acquire() as con:
            usage = await check_customer_advanced_analysis_usage(con, customer_id)
            if usage["jobs_reached"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usage limit reached and/or plan has expired",
                )
            await _validate_sources(con, token, details)
            await _validate_advanced_analysis_version(con, details.version)
            await create_advanced_analysis_job(
                con=con,
                sources=details.sources,
                queue=queue,
                priority=priority,
                meta=job_meta,
                user_id=user_id,
                customer_id=customer_id,
                job_type=details.job_type,
            )
    except HTTPException as e:
        logger.exception(f"Failed to create job: {e.detail}")
        raise
    except Exception:
        logger.exception("Failed to create job")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.delete("/advanced-analyses", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_advanced_analysis(
    request: Request,
    job_ids: list[uuid.UUID] = Query(None),  # type: ignore
    token=Depends(ProtectedAny(tag=ScopeTags.ADVANCED_ANALYSIS_WRITE)),
):
    try:
        # make sure at least one job ID was given
        if not job_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No job IDs given")
        # need to convert UUIDs to str to avoid issues with DB
        job_ids: list[str] = [str(job_id) for job_id in job_ids]
        user_id = str(uuid.UUID(token.userid))
        bind_context_to_logger({"user_id": user_id, "customer_id": token.customer_id, "job_ids": job_ids})

        async with request.state.pgpool.acquire() as con:
            await delete_advanced_analyses(con=con, user_id=user_id, job_ids=job_ids)
    except HTTPException as e:
        logger.exception(f"Failed to soft delete jobs: {e.detail}")
        raise
    except Exception:
        logger.exception("Failed to soft delete jobs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/advanced-analyses/download")
async def download_advanced_analysis(
    request: Request,
    details: PostAdvancedAnalysesDownloadRequest,
    token=Depends(ProtectedAny(tag=ScopeTags.ADVANCED_ANALYSIS_READ)),
):
    try:
        job_ids = details.job_ids
        # make sure at least one job ID was given
        if not job_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No job IDs given")
        # need to convert UUIDs to str to avoid issues with DB
        job_ids = [str(job_id) for job_id in job_ids]
        user_id = str(uuid.UUID(token.userid))
        bind_context_to_logger({"user_id": user_id, "customer_id": token.customer_id, "job_ids": job_ids})

        async with request.state.pgpool.acquire() as con:
            jobs = await _get_advanced_analyses_download_info(con, token, job_ids=job_ids)

        if not jobs:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job ID(s)")

        num_times_repeated = defaultdict(lambda: 0)

        filename_overrides = list()
        keys = list()

        for job in jobs:
            s3_prefix = job["s3_prefix"]
            filename = job["name"]
            obj_key = f"{s3_prefix}/{filename}"
            if not s3_prefix or not filename:
                logger.error(f"Invalid s3 prefix and or name for job: {obj_key}")
                continue
            keys.append(obj_key)

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
                "url": generate_presigned_url(
                    PULSE3D_UPLOADS_BUCKET, keys[0], filename_override=filename_overrides[0]
                )
            }
        else:
            # Grab ZIP file from in-memory, make response with correct MIME-type
            return StreamingResponse(
                content=stream_zip(
                    yield_s3_objects(bucket=PULSE3D_UPLOADS_BUCKET, keys=keys, filenames=filename_overrides)
                ),
                media_type="application/zip",
            )
    except HTTPException as e:
        logger.exception(f"Failed to download jobs: {e.detail}")
        raise
    except Exception:
        logger.exception("Failed to download jobs")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# HELPERS


async def _get_advanced_analyses_info(con, token, **retrieval_info):
    logger.info(f"Retrieving job info for {token.account_type}: {token.account_id}")

    match token.account_type:
        case "user":
            return await get_advanced_analyses_for_base_user(con, user_id=str(token.userid), **retrieval_info)
        case "admin":
            return await get_advanced_analyses_for_admin(
                con, customer_id=str(token.customer_id), **retrieval_info
            )


async def _validate_sources(con, token, details: PostAdvancedAnalysesRequest):
    """Check that the user submitting this job has access to the source jobs, and that the source jobs have the correct type"""
    if details.input_type in get_product_tags_of_user(token.scopes, rw_all_only=True):
        rows = await con.fetch(
            "SELECT j.job_id FROM jobs_result j JOIN uploads u ON j.upload_id=u.id "
            "WHERE j.status!='deleted' AND u.deleted='f' AND j.customer_id=$1 AND j.job_id=ANY($2::uuid[]) AND j.type=$3",
            token.customer_id,
            details.sources,
            details.input_type,
        )
    else:
        rows = await con.fetch(
            "SELECT j.job_id FROM jobs_result j JOIN uploads u ON j.upload_id=u.id "
            "WHERE j.status!='deleted' AND u.deleted='f' AND u.user_id=$1 AND j.job_id=ANY($2::uuid[]) AND j.type=$3",
            token.userid,
            details.sources,
            details.input_type,
        )

    valid_sources = set(row["job_id"] for row in rows)
    if invalid_sources := set(details.sources) - valid_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid source IDs: {invalid_sources}"
        )


async def _validate_advanced_analysis_version(con, version):
    version_status = await con.fetchrow(
        "SELECT state, end_of_life_date FROM advanced_analysis_versions WHERE version=$1", version
    )
    if version_status is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid version: {version}")

    status_name = version_status["state"]
    end_of_life_date = version_status["end_of_life_date"]
    if status_name == "deprecated" and (
        end_of_life_date is not None and datetime.strptime(end_of_life_date, "%Y-%m-%d") > datetime.now()
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid version: {version}")


# TODO move this to core/utils and share with other services that use it too
def _add_timestamp_to_filename(filename: str, timestamp: str) -> str:
    name, ext = os.path.splitext(filename)
    return f"{name}__{timestamp}{ext}"


async def _get_advanced_analyses_download_info(con, token, job_ids) -> list[dict[str, Any]]:
    logger.info(f"Downloading job IDs {job_ids} for {token.account_type}: {token.account_id}")

    match token.account_type:
        case "user":
            return await get_advanced_analyses_download_info_for_base_user(
                con=con, user_id=str(token.userid), job_ids=job_ids
            )
        case "admin":
            return await get_advanced_analyses_download_info_for_admin(
                con=con, customer_id=str(token.customer_id), job_ids=job_ids
            )
        case invalid_account_type:
            raise Exception(f"Invalid account type: {invalid_account_type}")
