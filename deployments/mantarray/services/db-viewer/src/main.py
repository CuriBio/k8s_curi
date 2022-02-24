from fastapi import FastAPI
<<<<<<< HEAD
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
=======
from fastapi.templating import Jinja2Templates
from fastapi import Request
import pymysql
import os

# from .aws_utils import get_ssm_secrets

# DB_CLUSTER_ENDPOINT = os.environ.get("DB_CLUSTER_ENDPOINT")

# username, password = get_ssm_secrets()
# INFO_DICT = {
#     "db_username": username,
#     "db_password": password,
#     "db_name": "mantarray_units",
# }

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# def get_db_connection():
#     return pymysql.connect(
#         host=DB_CLUSTER_ENDPOINT,
#         user=INFO_DICT["db_username"],
#         passwd=INFO_DICT["db_password"],
#         db=INFO_DICT["db_name"],
#     )
>>>>>>> renamed deployment


@app.get("/")
async def root(request: Request):
<<<<<<< HEAD
    with db_reader_connection.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT * FROM MAUnits;")
        results = cur.fetchall()
        units = [{col: row[col] for col in ("serial_number", "hw_version")} for row in results]
        return templates.TemplateResponse("table.html", {"request": request, "units": units})
=======
    # db = get_db_connection()
    units = [{"serial_number": "1", "hw_version": "2.2.0"}, {"serial_number": "2", "hw_version": "2.2.2"}]
    return templates.TemplateResponse(
        "table.html",
        {"request": request, "units": units},
    )
>>>>>>> renamed deployment
