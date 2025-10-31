from starlette.config import Config
from starlette.datastructures import Secret

config = Config(".env")
# version used to tag the docker image
VERSION = "0.10.6"

DASHBOARD_URL = config("DASHBOARD_URL", cast=str, default="https://dashboard.curibio-test.com")

CLUSTER_NAME = config("CLUSTER_NAME", cast=str, default="test")
POSTGRES_USER = config("POSTGRES_USER", cast=str)
POSTGRES_PASSWORD = config("POSTGRES_PASSWORD", cast=Secret)
POSTGRES_SERVER = config("POSTGRES_SERVER", cast=str, default="localhost")
POSTGRES_PORT = config("POSTGRES_PORT", cast=str, default="5432")
POSTGRES_DB = config("POSTGRES_DB", cast=str)

DATABASE_URL = config(
    "DATABASE_URL",
    cast=str,
    default=f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}",
)
