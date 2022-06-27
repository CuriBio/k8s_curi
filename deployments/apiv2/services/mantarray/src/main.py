import logging

from fastapi import Depends, FastAPI, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from auth import ProtectedAny
from core.config import DATABASE_URL
from core.firmware import get_download_url
from core.firmware import resolve_versions
from utils.db import AsyncpgPoolDep


# logging is configured in log_config.yaml
logger = logging.getLogger(__name__)


AUTH = ProtectedAny()  # TODO add scope here


app = FastAPI(openapi_url=None)
templates = Jinja2Templates(directory="templates")

asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.pgpool = await asyncpg_pool()
    response = await call_next(request)
    return response


@app.on_event("startup")
async def startup():
    await asyncpg_pool()


@app.get("/")
async def root(request: Request):
    async with request.state.pgpool.acquire() as con:
        rows = await con.fetch("SELECT * FROM MAUnits")
        # convert to dicts for us in jinja template
        units = [dict(row) for row in rows]
    return templates.TemplateResponse("table.html", {"request": request, "units": units})


@app.get("/firmware_latest")
async def get_latest_firmware(request: Request, serial_number: str):
    async with request.state.pgpool.acquire() as con:
        # get hardware version from serial number
        try:
            row = await con.fetchrow("SELECT hw_version FROM MAUnits WHERE serial_number = $1", serial_number)
            hardware_version = row["hw_version"]
        except Exception as e:
            err_msg = f"Serial Number {serial_number} not found"
            logger.error(f"{err_msg}: {repr(e)}")
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": err_msg})
    # try to get latest FW versions from HW version
    try:
        latest_versions = resolve_versions(hardware_version)
        return JSONResponse({"latest_versions": latest_versions})
    except Exception as e:
        err_msg = f"Error getting latest FW versions for {serial_number} with HW version {hardware_version}"
        logger.error(f"{err_msg}: {repr(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": err_msg})


@app.get("/firmware_download")
async def get_firmware_download_url(
    firmware_version: str = Query(..., regex=r"^\d+\.\d+\.\d+$"),
    firmware_type: str = Query(..., regex="^(main|channel)$"),
    token=Depends(AUTH),
):
    try:
        url = get_download_url(firmware_version, firmware_type)
        return JSONResponse({"presigned_url": url})
    except Exception as e:
        err_msg = f"{firmware_type.title()} Firmware v{firmware_version} not found"
        logger.error(f"{err_msg}: {repr(e)}")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": err_msg})
