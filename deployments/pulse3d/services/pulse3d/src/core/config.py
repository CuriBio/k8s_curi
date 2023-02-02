from starlette.config import Config
from starlette.datastructures import Secret

config = Config(".env")
# version used to tag the docker image
VERSION = "0.5.4"

APP_NAME = config("APP_NAME", cast=str, default="CuriBio/Pulse3d")
JWT_SECRET_KEY = config("JWT_SECRET_KEY", cast=Secret)
JWT_ALGORITHM = config("JWT_ALGORITHM", cast=str, default="HS256")
JWT_AUDIENCE = config("JWT_AUDIENCE", cast=str, default="curibio:auth")
JWT_TOKEN_PREFIX = config("JWT_TOKEN_PREFIX", cast=str, default="Bearer")

POSTGRES_USER = config("POSTGRES_USER", cast=str)
POSTGRES_PASSWORD = config("POSTGRES_PASSWORD", cast=Secret)
POSTGRES_SERVER = config("POSTGRES_SERVER", cast=str, default="localhost")
POSTGRES_PORT = config("POSTGRES_PORT", cast=str, default="5432")
POSTGRES_DB = config("POSTGRES_DB", cast=str)

DASHBOARD_URL = config("DASHBOARD_URL", cast=str, default="https://dashboard.curibio-test.com")

PULSE3D_UPLOADS_BUCKET = config("UPLOADS_BUCKET_ENV", cast=str, default="test-pulse3d-uploads")
MANTARRAY_LOGS_BUCKET = config("MANTARRAY_LOGS_BUCKET_ENV", cast=str, default="test-mantarray-logs")

DATABASE_URL = config(
    "DATABASE_URL",
    cast=str,
    default=f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}",
)
