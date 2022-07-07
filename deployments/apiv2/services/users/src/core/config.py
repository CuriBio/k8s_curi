from starlette.config import Config
from starlette.datastructures import Secret

config = Config(".env")

APP_NAME = config("APP_NAME", cast=str, default="CuriBio/Auth")

# POSTGRES_USER = config("POSTGRES_USER", cast=str)
# POSTGRES_PASSWORD = config("POSTGRES_PASSWORD", cast=Secret)
# POSTGRES_SERVER = config("POSTGRES_SERVER", cast=str, default="localhost")
# POSTGRES_PORT = config("POSTGRES_PORT", cast=str, default="5432")
# POSTGRES_DB = config("POSTGRES_DB", cast=str)

# DATABASE_URL = config(
#     "DATABASE_URL",
#     cast=str,
#     default=f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}",
# )

DATABASE_URL = config(
    "DATABASE_URL",
    cast=str,
    default=f"postgresql://root:HjnlH9RaeTt7uRuF7Uwco6BX4l0jgp39@localhost:5556/curibio",
)