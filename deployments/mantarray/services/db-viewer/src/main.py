from contextlib import contextmanager
from fastapi import FastAPI
from fastapi import Request
from fastapi.templating import Jinja2Templates
from immutabledict import immutabledict
from psycopg2.extras import DictCursor
from psycopg2.pool import ThreadedConnectionPool

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


# based on https://stackoverflow.com/questions/55451707/how-to-ensure-connection-closing-when-im-having-multiple-connections-declared
@contextmanager
def get_connection(connection_pool):
    conn = connection_pool.getconn()
    try:
        yield conn
    finally:
        connection_pool.putconn(conn)


@contextmanager
def get_cursor(connection):
    cur = connection.cursor(cursor_factory=DictCursor)
    try:
        yield cur
    finally:
        cur.close()


@app.get("/")
async def root(request: Request):
    with get_connection(db_reader_connection_pool) as reader_conn:
        with get_cursor(reader_conn) as cur:
            cur.execute("SELECT * FROM MAUnits;")
            results = cur.fetchall()
            units = [{col: row[col] for col in ("serial_number", "hw_version")} for row in results]
            return templates.TemplateResponse("table.html", {"request": request, "units": units})


db_reader_connection_pool = ThreadedConnectionPool(1, 3, database="postgres", **get_db_connect_info("reader"))
# db_writer_connection_pool = ThreadedConnectionPool(1, 1, database="postgres", **get_db_connect_info("writer"))
