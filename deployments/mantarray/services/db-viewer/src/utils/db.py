from contextlib import contextmanager
from immutabledict import immutabledict
from psycopg2.extras import DictCursor
from psycopg2.pool import ThreadedConnectionPool

from utils.aws import get_db_secrets

DB_SECRETS_DICT = immutabledict(get_db_secrets())


def get_db_connect_info(connection_type: str):
    connection_kwargs = dict(DB_SECRETS_DICT)
    connection_kwargs["host"] = connection_kwargs[f"{connection_type}_endpoint"]
    del connection_kwargs["reader_endpoint"]
    del connection_kwargs["writer_endpoint"]
    return connection_kwargs


CONNECTION_POOLS = immutabledict(
    {
        "reader": ThreadedConnectionPool(1, 3, database="postgres", **get_db_connect_info("reader")),
        "writer": ThreadedConnectionPool(1, 1, database="postgres", **get_db_connect_info("writer")),
    }
)


# based on https://stackoverflow.com/questions/55451707/how-to-ensure-connection-closing-when-im-having-multiple-connections-declared
@contextmanager
def _get_connection(connection_pool):
    conn = connection_pool.getconn()
    try:
        yield conn
    finally:
        connection_pool.putconn(conn)


@contextmanager
def _get_cursor(connection):
    cur = connection.cursor(cursor_factory=DictCursor)
    try:
        yield cur
    finally:
        cur.close()


def get_cursor(pool_type):
    connection_pool = CONNECTION_POOLS[pool_type]

    def _cursor_gen():
        with _get_connection(connection_pool) as conn:
            with _get_cursor(conn) as cur:
                yield cur

    return _cursor_gen
