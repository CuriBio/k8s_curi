from contextlib import asynccontextmanager
import time
import uuid

from fastapi import FastAPI, Request, Response, Depends, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette_context import context, request_cycle_context
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from uvicorn.protocols.utils import get_path_with_query_string

from auth import ProtectedAny, ScopeTags
from jobs import check_customer_advanced_analysis_usage
from utils.db import AsyncpgPoolDep
from utils.logging import setup_logger, bind_context_to_logger
from core.config import DATABASE_URL, DASHBOARD_URL

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


@app.get("/usage")
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


@app.get("/advanced-analyses")
async def get_advanced_analyses(request: Request):
    "TODO"  # need to support server side filtering here


@app.post("/advanced-analyses")
async def create_new_advanced_analysis(request: Request):
    "TODO"


@app.delete("/advanced-analyses/{job_id}")
async def delete_advanced_analysis(request: Request):
    "TODO"


@app.post("/advanced-analyses/download")
async def download_advanced_analysis(request: Request):
    "TODO"
