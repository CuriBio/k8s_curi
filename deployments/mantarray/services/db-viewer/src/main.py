from fastapi import FastAPI
from fastapi import Request
from fastapi.templating import Jinja2Templates
from immutabledict import immutabledict
import psycopg2
from psycopg2.extras import DictCursor

from utils.aws_utils import get_db_secrets

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DB_SECRETS_DICT = immutabledict(get_db_secrets())


def get_db_connect_info(connection_type: str):
    connection_kwargs = dict(DB_SECRETS_DICT)
    connection_kwargs["host"] = connection_kwargs[f"{connection_type}_endpoint"]
    del connection_kwargs["reader_endpoint"]
    del connection_kwargs["writer_endpoint"]
    return connection_kwargs


db_reader_connection = psycopg2.connect(database="postgres", **get_db_connect_info("reader"))
db_writer_connection = psycopg2.connect(database="postgres", **get_db_connect_info("writer"))


@app.get("/")
async def root(request: Request):
    with db_reader_connection.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM MAUnits;")
        results = cur.fetchall()
        units = [{col: row[col] for col in ("serial_number", "hw_version")} for row in results]
        return templates.TemplateResponse("table.html", {"request": request, "units": units})
