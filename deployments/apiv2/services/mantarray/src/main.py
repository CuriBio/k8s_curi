import time

from fastapi import Depends, FastAPI, Path, Request, status, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from structlog.threadlocal import bind_threadlocal, clear_threadlocal
from uvicorn.protocols.utils import get_path_with_query_string

from auth import ProtectedAny
from core.config import DATABASE_URL, DASHBOARD_URL
from core.versions import get_download_url, get_required_sw_version_range, resolve_versions
from models.responses import MantarrayUnitsResponse, SerialNumberRequest
from utils.db import AsyncpgPoolDep
from utils.logging import setup_logger

setup_logger()
logger = structlog.stdlib.get_logger("api.access")


app = FastAPI(openapi_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[DASHBOARD_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next) -> Response:
    request.state.pgpool = await asyncpg_pool()
    # clear previous request variables
    clear_threadlocal()
    # get request details for logging
    if (client_ip := request.headers.get("X-Forwarded-For")) is None:
        client_ip = f"{request.client.host}:{request.client.port}"

    url = get_path_with_query_string(request.scope)
    http_method = request.method
    http_version = request.scope["http_version"]
    start_time = time.perf_counter_ns()

    # bind details to logger
    bind_threadlocal(url=str(request.url), method=http_method, client_ip=client_ip)

    response = await call_next(request)

    process_time = time.perf_counter_ns() - start_time
    status_code = response.status_code

    logger.info(
        f"""{client_ip} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
        status_code=status_code,
        duration=process_time / 10**9,
    )

    return response


@app.on_event("startup")
async def startup():
    await asyncpg_pool()


# TODO make request and response models for all of these?


@app.get("/serial-number", response_model=MantarrayUnitsResponse)
async def root(request: Request):
    try:
        async with request.state.pgpool.acquire() as con:
            units = await con.fetch("SELECT * FROM MAUnits")
    except:
        logger.exception("Error getting Mantarray Units")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return MantarrayUnitsResponse(units=units)


# TODO add serial number validation?
@app.post("/serial-number", status_code=status.HTTP_204_NO_CONTENT)
async def add_serial_number(
    request: Request,
    details: SerialNumberRequest,
    token=Depends(ProtectedAny(scope=["mantarray:serial_number:edit"])),
):
    try:
        bind_threadlocal(
            user_id=token.get("userid"),
            customer_id=token.get("customer_id"),
            serial_number=details.serial_number,
        )

        async with request.state.pgpool.acquire() as con:
            await con.execute(
                "INSERT INTO MAUnits VALUES ($1, $2)", details.serial_number, details.hw_version
            )
    except Exception:
        logger.exception("Error adding serial number")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.delete("/serial-number/{serial_number}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_serial_number(
    request: Request,
    serial_number: str = Path(...),
    token=Depends(ProtectedAny(scope=["mantarray:serial_number:edit"])),
):
    try:
        bind_threadlocal(
            user_id=token.get("userid"), customer_id=token.get("customer_id"), serial_number=serial_number
        )

        async with request.state.pgpool.acquire() as con:
            await con.execute("DELETE FROM MAUnits WHERE serial_number=$1", serial_number)
    except Exception:
        logger.exception("Error deleting serial number")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/software-range/{main_fw_version}")
async def get_software_for_main_fw(
    request: Request, main_fw_version: str = Path(..., regex=r"^\d+\.\d+\.\d+$")
):
    """Get the max/min SW version compatible with the given main firmware version."""
    try:
        max_min_version_dict = get_required_sw_version_range(main_fw_version)
        return JSONResponse(max_min_version_dict)
    except Exception:
        err_msg = f"Error getting the required SW version for main FW v{main_fw_version}"
        logger.exception(err_msg)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": err_msg})


@app.get("/versions/{serial_number}")
async def get_latest_versions(request: Request, serial_number: str):
    """Get the latest SW, main FW, and channel FW versions compatible with the MA instrument with the given serial number."""
    async with request.state.pgpool.acquire() as con:
        bind_threadlocal(serial_number=serial_number)
        # get hardware version from serial number
        try:
            row = await con.fetchrow("SELECT hw_version FROM MAUnits WHERE serial_number=$1", serial_number)
            hardware_version = row["hw_version"]
            bind_threadlocal(hardware_version=hardware_version)
        except Exception:
            err_msg = f"Serial Number {serial_number} not found"
            logger.exception(err_msg)
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": err_msg})
    # try to get latest FW versions from HW version
    try:
        latest_versions = resolve_versions(hardware_version)
        return JSONResponse({"latest_versions": latest_versions})
    except Exception:
        err_msg = f"Error getting latest FW versions for {serial_number} with HW version {hardware_version}"
        logger.exception(err_msg)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": err_msg})


@app.get("/firmware/{fw_type}/{version}")
async def get_firmware_download_url(
    fw_type: str = Path(..., regex="^(main|channel)$"),
    version: str = Path(..., regex=r"^\d+\.\d+\.\d+$"),
    token=Depends(ProtectedAny(scope=["mantarray:firmware:get"])),
):
    try:
        bind_threadlocal(fw_type=fw_type, fw_version=version)

        url = get_download_url(version, fw_type)
        return JSONResponse({"presigned_url": url})
    except Exception:
        err_msg = f"{fw_type.title()} Firmware v{version} not found"
        logger.exception(err_msg)
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": err_msg})
