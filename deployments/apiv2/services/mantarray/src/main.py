from fastapi import Depends
from fastapi import FastAPI
from fastapi import Query
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from utils.db import get_cursor
from utils.firmware import get_download_url
from utils.firmware import get_latest_firmware_version


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
    hardware_version = cur.fetchone()[0]
    latest_firmware_version = get_latest_firmware_version(hardware_version)
    return JSONResponse({"latest_versions": latest_firmware_version})


@app.get("/firmware_download")
async def get_firmware_download_url(
    firmware_version: str = Query(..., regex=r"^\d+\.\d+\.\d+$"),
    firmware_type: str = Query(..., regex="^(main|channel)$"),
):
    # TODO add auth
    url = get_download_url(firmware_version, firmware_type)
    return JSONResponse({"presigned_url": url})
