from starlette.config import Config
from starlette.datastructures import Secret

config = Config(".env")

APP_NAME = config("APP_NAME", cast=str, default="CuriBio/Auth")
# version used to tag the docker image
VERSION = "0.7.9"

DASHBOARD_URL = config("DASHBOARD_URL", cast=str, default="https://dashboard.curibio-test.com")
CURIBIO_EMAIL = config("CURIBIO_EMAIL", cast=str)
CURIBIO_EMAIL_PASSWORD = config("CURIBIO_EMAIL_PASSWORD", cast=str)

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
