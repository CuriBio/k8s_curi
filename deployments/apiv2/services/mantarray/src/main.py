import logging

from fastapi import Depends, FastAPI, Path, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from auth import ProtectedAny
from core.config import DATABASE_URL, DASHBOARD_URL
from core.versions import get_download_url, get_required_sw_version_range, resolve_versions
from models.responses import MantarrayUnitsResponse
from utils.db import AsyncpgPoolDep


# logging is configured in log_config.yaml
logger = logging.getLogger(__name__)


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
async def db_session_middleware(request: Request, call_next):
    request.state.pgpool = await asyncpg_pool()
    response = await call_next(request)

    return response


@app.on_event("startup")
async def startup():
    await asyncpg_pool()


# TODO make request and response models for all of these?


# TODO change this to /serial-number ?
@app.get("/", response_model=MantarrayUnitsResponse)
async def root(request: Request):
    try:
        async with request.state.pgpool.acquire() as con:
            units = await con.fetch("SELECT * FROM MAUnits")
    except:
        logger.exception("Error getting Mantarray Units")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return MantarrayUnitsResponse(units=units)


# TODO add serial number validation?
@app.post("/serial-number/{serial_number}", status_code=status.HTTP_204_NO_CONTENT)
async def add_serial_number(
    request: Request,
    serial_number: str = Path(...),
    token=Depends(ProtectedAny(scope=["mantarray:serial_number:edit"])),
):
    try:
        async with request.state.pgpool.acquire() as con:
            await con.execute("INSERT INTO MAUnits VALUES ($1, '1.0.0')", serial_number)
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
        # get hardware version from serial number
        try:
            row = await con.fetchrow("SELECT hw_version FROM MAUnits WHERE serial_number=$1", serial_number)
            hardware_version = row["hw_version"]
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
        url = get_download_url(version, fw_type)
        return JSONResponse({"presigned_url": url})
    except Exception:
        err_msg = f"{fw_type.title()} Firmware v{version} not found"
        logger.exception(err_msg)
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": err_msg})
