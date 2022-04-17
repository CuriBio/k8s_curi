from fastapi import Depends, FastAPI, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from auth import ProtectedAny
from utils.db import get_cursor
from utils.firmware import get_download_url
from utils.firmware import resolve_versions


AUTH = ProtectedAny()


app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root(request: Request, cur=Depends(get_cursor("reader"))):
    cur.execute("SELECT * FROM MAUnits")
    results = cur.fetchall()
    units = [{col: row[col] for col in ("serial_number", "hw_version")} for row in results]
    return templates.TemplateResponse("table.html", {"request": request, "units": units})


@app.get("/firmware_latest")
async def get_latest_firmware(serial_number: str, cur=Depends(get_cursor("reader"))):
    cur.execute("SELECT hw_version FROM MAUnits WHERE serial_number = '$1'", serial_number)
    # get hardware version from serial number
    try:
        hardware_version = cur.fetchone()[0]
    except:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": f"Serial Number {serial_number} not found"},
        )
    # try to get latest FW versions from HW version
    try:
        latest_firmware_versions = resolve_versions(hardware_version)
        return JSONResponse({"latest_versions": latest_firmware_versions})
    except:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "TODO"},
        )


@app.get("/firmware_download")
async def get_firmware_download_url(
    firmware_version: str = Query(..., regex=r"^\d+\.\d+\.\d+$"),
    firmware_type: str = Query(..., regex="^(main|channel)$"),
    token=Depends(AUTH),  # TODO add scope here
):
    try:
        url = get_download_url(firmware_version, firmware_type)
        return JSONResponse({"presigned_url": url})
    except:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"{firmware_type.title()} Firmware v{firmware_version} not found",
        )
