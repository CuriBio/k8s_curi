import time

from contextlib import asynccontextmanager
from asyncpg.exceptions import UniqueViolationError
from fastapi import Depends, FastAPI, Path, Request, status, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import semver
from starlette_context import context, request_cycle_context
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from uvicorn.protocols.utils import get_path_with_query_string

from auth import ProtectedAny, Scopes
from core.config import CLUSTER_NAME, DATABASE_URL, DASHBOARD_URL
from core.versions import get_fw_download_url, get_required_sw_version_range, get_latest_compatible_versions
from models.models import (
    ChannelFirmwareUpdateRequest,
    FirmwareUploadResponse,
    MantarrayUnitsResponse,
    SerialNumberRequest,
    FirmwareInfoResponse,
    MainFirmwareUploadRequest,
    ChannelFirmwareUploadRequest,
    LatestVersionsResponse,
)
from utils.db import AsyncpgPoolDep
from utils.logging import setup_logger, bind_context_to_logger
from utils.s3 import generate_presigned_post

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
async def db_session_middleware(request: Request, call_next) -> Response:
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

    # bind details to logger
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


SEMVER_REGEX = r"^\d+\.\d+\.\d+$"
FW_TYPE_REGEX = "^(main|channel)$"
SW_TYPE_REGEX = "^(mantarray|stingray)$"


# TODO make request and response models for all of these?


# ROUTES
@app.get("/serial-number", response_model=MantarrayUnitsResponse)
async def root(request: Request):
    try:
        async with request.state.pgpool.acquire() as con:
            units = await con.fetch("SELECT * FROM MAUnits")
        units = [dict(row) for row in units]
    except:
        logger.exception("Error getting Mantarray Units")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return MantarrayUnitsResponse(units=units)


@app.post("/serial-number", status_code=status.HTTP_201_CREATED)
async def add_serial_number(
    request: Request,
    details: SerialNumberRequest,
    token=Depends(ProtectedAny(scopes=[Scopes.MANTARRAY__SERIAL_NUMBER__EDIT])),
):
    try:
        bind_context_to_logger(
            {
                "user_id": token.userid,
                "customer_id": token.customer_id,
                "serial_number": details.serial_number,
            }
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
    token=Depends(ProtectedAny(scopes=[Scopes.MANTARRAY__SERIAL_NUMBER__EDIT])),
):
    try:
        bind_context_to_logger(
            {"user_id": token.userid, "customer_id": token.customer_id, "serial_number": serial_number}
        )

        async with request.state.pgpool.acquire() as con:
            await con.execute("DELETE FROM MAUnits WHERE serial_number=$1", serial_number)
    except Exception:
        logger.exception("Error deleting serial number")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# TODO Tanner (1/25/24): this is kept here to support backwards compatibility with older controller versions. It can be removed once all users upgrade to the controller versions released after the date of this note
@app.get("/software-range/{main_fw_version}")
async def get_prod_software_for_main_fw(
    request: Request, main_fw_version: str = Path(..., pattern=SEMVER_REGEX)
):
    return await _get_software_range(request, main_fw_version, True)


@app.get("/software-range/{main_fw_version}/{prod}")
async def get_software_for_main_fw(
    request: Request, prod: bool, main_fw_version: str = Path(..., pattern=SEMVER_REGEX)
):
    return await _get_software_range(request, main_fw_version, prod)


async def _get_software_range(request: Request, main_fw_version: str, prod: bool):
    """Get the max/min SW version compatible with the given main firmware version."""
    try:
        async with request.state.pgpool.acquire() as con:
            main_fw_compatibility = await con.fetch(
                "SELECT version AS main_fw_version, min_ma_controller_version, min_sting_controller_version "
                "FROM ma_main_firmware"
            )
            ma_sw_versions = await con.fetch("SELECT version, state FROM ma_controllers")
            sting_sw_versions = await con.fetch("SELECT version, state FROM sting_controllers")

        max_min_version_dict = get_required_sw_version_range(
            main_fw_version, main_fw_compatibility, ma_sw_versions, sting_sw_versions, prod
        )
        return JSONResponse(max_min_version_dict)
    except Exception:
        err_msg = f"Error getting the required SW version for main FW v{main_fw_version}"
        logger.exception(err_msg)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": err_msg})


# TODO Tanner (1/25/24): this is kept here to support backwards compatibility with older controller versions. It can be removed once all users upgrade to the controller versions released after the date of this note
@app.get("/versions/{serial_number}")
async def get_latest_prod_versions(request: Request, serial_number: str):
    latest_versions = await _get_latest_versions(request, serial_number, True)
    return JSONResponse(
        {
            "latest_versions": {
                "sw": latest_versions["min_ma_controller_version"],
                "main-fw": latest_versions["main_fw_version"],
                "channel-fw": latest_versions["channel_fw_version"],
            }
        }
    )


@app.get("/versions/{serial_number}/{prod}")
async def get_latest_versions(request: Request, serial_number: str, prod: bool):
    latest_versions = await _get_latest_versions(request, serial_number, prod)
    return LatestVersionsResponse(
        ma_sw=latest_versions["min_ma_controller_version"],
        sting_sw=latest_versions["min_sting_controller_version"],
        main_fw=latest_versions["main_fw_version"],
        channel_fw=latest_versions["channel_fw_version"],
    )


async def _get_latest_versions(request: Request, serial_number: str, prod: bool):
    """Get the latest SW, main FW, and channel FW versions compatible with the MA instrument with the given serial number."""
    bind_context_to_logger({"serial_number": serial_number, "is_prod_controller": prod})

    compat_query = (
        "SELECT m.min_ma_controller_version, m.min_sting_controller_version, m.version AS main_fw_version, c.version AS channel_fw_version "
        "FROM ma_channel_firmware AS c "
        "JOIN ma_main_firmware AS m ON c.main_fw_version=m.version "
        "JOIN maunits AS u ON c.hw_version=u.hw_version "
        "WHERE u.serial_number=$1 "
    )
    if prod:
        compat_query += "AND c.state='external'"

    async with request.state.pgpool.acquire() as con:
        try:
            all_compatible_versions = await con.fetch(compat_query, serial_number)
        except Exception:
            logger.exception(f"Serial Number {serial_number} not found")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        all_main_fw_versions = await con.fetch("SELECT version, state FROM ma_main_firmware")

    all_compatible_versions = [dict(row) for row in all_compatible_versions]
    all_main_fw_versions = [dict(row) for row in all_main_fw_versions]

    try:
        latest_versions = get_latest_compatible_versions(all_compatible_versions, all_main_fw_versions, prod)
    except Exception:
        err_msg = f"Error determining latest FW + SW versions for {serial_number}"
        logger.exception(err_msg)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": err_msg})

    return latest_versions


@app.get("/firmware/info")
async def get_all_fw_sw_compatibility(
    request: Request, token=Depends(ProtectedAny(scopes=[Scopes.MANTARRAY__FIRMWARE__LIST]))
):
    try:
        async with request.state.pgpool.acquire() as con:
            main_fw_info = await con.fetch("SELECT * FROM ma_main_firmware")
            channel_fw_info = await con.fetch("SELECT * FROM ma_channel_firmware")
            latest_ma_version = _get_min_compatible_sw_version(
                await con.fetch("SELECT version, state FROM ma_controllers"), True
            )
            latest_sting_version = _get_min_compatible_sw_version(
                await con.fetch("SELECT version, state FROM sting_controllers"), True
            )

        main_fw_info = [dict(row) for row in main_fw_info]
        channel_fw_info = [dict(row) for row in channel_fw_info]

        return FirmwareInfoResponse(
            main_fw_info=main_fw_info,
            channel_fw_info=channel_fw_info,
            latest_ma_version=latest_ma_version,
            latest_sting_version=latest_sting_version,
        )
    except Exception:
        logger.exception("Error getting FW/SW compatibility")
        raise


@app.get("/firmware/{fw_type}/{version}")
async def get_firmware_download_url(
    fw_type: str = Path(..., pattern=FW_TYPE_REGEX),
    version: str = Path(..., pattern=SEMVER_REGEX),
    token=Depends(ProtectedAny(scopes=[Scopes.MANTARRAY__FIRMWARE__GET])),
):
    try:
        bind_context_to_logger({"fw_type": fw_type, "fw_version": version})

        url = get_fw_download_url(version, fw_type)
        return JSONResponse({"presigned_url": url})
    except Exception:
        err_msg = f"{fw_type.title()} Firmware v{version} not found"
        logger.exception(err_msg)
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": err_msg})


@app.post("/firmware/{fw_type}/{version}")
async def upload_firmware_file(
    request: Request,
    details: MainFirmwareUploadRequest | ChannelFirmwareUploadRequest,
    fw_type: str = Path(..., pattern=FW_TYPE_REGEX),
    version: str = Path(..., pattern=SEMVER_REGEX),
    token=Depends(ProtectedAny(scopes=[Scopes.MANTARRAY__FIRMWARE__EDIT])),
):
    bind_context_to_logger({"fw_type": fw_type, "fw_version": version})

    async with request.state.pgpool.acquire() as con:
        if fw_type == "main":
            min_ma_controller_version = _get_min_compatible_sw_version(
                await con.fetch("SELECT version, state FROM ma_controllers"),
                details.is_compatible_with_current_ma_sw,
            )
            min_sting_controller_version = _get_min_compatible_sw_version(
                await con.fetch("SELECT version, state FROM sting_controllers"),
                details.is_compatible_with_current_sting_sw,
            )

            query_args = (
                "INSERT INTO ma_main_firmware (version, min_ma_controller_version, min_sting_controller_version) VALUES ($1, $2, $3)",
                version,
                min_ma_controller_version,
                min_sting_controller_version,
            )
        else:
            query_args = (
                "INSERT INTO ma_channel_firmware (version, main_fw_version, hw_version) VALUES ($1, $2, $3)",
                version,
                details.main_fw_version,
                details.hw_version,
            )

        # create upload url before inserting FW version into DB so that if this step fails the DB insertion won't happen
        try:
            upload_params = generate_presigned_post(
                bucket=f"{CLUSTER_NAME}-{fw_type}-firmware", key=f"{version}.bin", md5s=details.md5s
            )
        except Exception:
            logger.exception(f"Error generating presigned post for {fw_type} firmware v{version}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            await con.execute(*query_args)
        except Exception:
            err_msg = f"Error adding {fw_type} firmware v{version} to DB"
            logger.exception(err_msg)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err_msg))

    return FirmwareUploadResponse(params=upload_params)


@app.put("/firmware/channel/{version}")
async def update_firmware_info(
    request: Request,
    details: ChannelFirmwareUpdateRequest,
    version: str = Path(..., pattern=SEMVER_REGEX),
    token=Depends(ProtectedAny(scopes=[Scopes.MANTARRAY__FIRMWARE__EDIT])),
):
    bind_context_to_logger({"fw_version": version})

    # currently the only thing that needs to be updated through this route is the main FW version tied to a channel FW version
    try:
        async with request.state.pgpool.acquire() as con:
            await con.execute(
                "UPDATE ma_channel_firmware SET main_fw_version=$1 WHERE version=$2",
                details.main_fw_version,
                version,
            )
    except Exception:
        logger.exception(f"Error updating channel firmware v{version}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/software/{controller}/{version}/{prod}")
async def add_software_version(
    request: Request,
    prod: bool,
    controller: str = Path(..., pattern=SW_TYPE_REGEX),
    version: str = Path(..., pattern=SEMVER_REGEX),
    token=Depends(ProtectedAny(scopes=[Scopes.MANTARRAY__SOFTWARE__EDIT])),
):
    bind_context_to_logger({"controller_type": controller, "sw_version": version})

    state = "external" if prod else "internal"

    if controller == "mantarray":
        query = "INSERT INTO ma_controllers (version, state) VALUES ($1, $2)"
    else:
        query = "INSERT INTO sting_controllers (version, state) VALUES ($1, $2)"

    try:
        async with request.state.pgpool.acquire() as con:
            await con.execute(query, version, state)

    except UniqueViolationError:
        if prod:
            if controller == "mantarray":
                query = "UPDATE ma_controllers SET state='external' WHERE version=$1"
            else:
                query = "UPDATE sting_controllers SET state='external' WHERE version=$1"
            async with request.state.pgpool.acquire() as con:
                await con.execute(query, version)
    except Exception:
        err_msg = f"Error adding {controller} controller v{version} to DB"
        logger.exception(err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err_msg))


# HELPERS


def _get_min_compatible_sw_version(sw_version_rows, is_compatible):
    max_sw_version_on_prod_channel = sorted(
        [semver.Version.parse(row["version"]) for row in sw_version_rows if row["state"] == "external"]
    )[-1]

    if is_compatible:
        min_compatible_sw_version = max_sw_version_on_prod_channel
    else:
        # just bump the patch version
        min_compatible_sw_version = max_sw_version_on_prod_channel.bump_patch()

    return str(min_compatible_sw_version)
