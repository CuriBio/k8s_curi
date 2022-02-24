from fastapi import FastAPI
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


@app.get("/")
async def root(request: Request):
    # db = get_db_connection()
    units = [{"serial_number": "1", "hw_version": "2.2.0"}, {"serial_number": "2", "hw_version": "2.2.2"}]
    return templates.TemplateResponse(
        "table.html",
        {"request": request, "units": units},
    )
