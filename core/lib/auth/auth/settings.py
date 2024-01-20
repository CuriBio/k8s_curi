from starlette.config import Config
from starlette.datastructures import Secret

config = Config(".env")

ACCESS_TOKEN_EXPIRE_MINUTES = config("ACCESS_TOKEN_EXPIRE_MINUTES", cast=int, default=5)  # 5 minutes
REFRESH_TOKEN_EXPIRE_MINUTES = config("REFRESH_TOKEN_EXPIRE_MINUTES", cast=int, default=30)  # 30 minutes
EMAIL_VER_TOKEN_EXPIRE_MINUTES = config("EMAIL_VER_TOKEN_EXPIRE_MINUTES", cast=int, default=1440)  # 24hrs
COOKIE_MAX_AGE_SECONDS = config(
    "COOKIE_MAX_AGE_SECONDS", cast=int, default=REFRESH_TOKEN_EXPIRE_MINUTES * 60
)  # 30 min

JWT_SECRET_KEY = config("JWT_SECRET_KEY", cast=Secret)
JWT_ALGORITHM = config("JWT_ALGORITHM", cast=str, default="HS256")
JWT_AUDIENCE = config("JWT_AUDIENCE", cast=str, default="curibio:auth")
JWT_TOKEN_PREFIX = config("JWT_TOKEN_PREFIX", cast=str, default="Bearer")
