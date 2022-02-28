from fastapi import Depends
from fastapi import FastAPI
from fastapi import Request
from fastapi.templating import Jinja2Templates

from utils.db import get_cursor


app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root(request: Request, cur=Depends(get_cursor("reader"))):
    cur.execute("SELECT * FROM MAUnits;")
    results = cur.fetchall()
    units = [{col: row[col] for col in ("serial_number", "hw_version")} for row in results]
    return templates.TemplateResponse("table.html", {"request": request, "units": units})
