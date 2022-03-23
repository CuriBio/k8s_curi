import asyncio
import asyncpg
import json
import jwt
import logging
import uuid


from datetime import datetime, timedelta, timezone
from calendar import timegm

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth import AccessToken, ProtectedAny, create_token
from core.db import Database
from models.users import UserLogin, UserCreate, UserProfile
from models.errors import LoginError, RegistrationError


logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

db = Database()
app = FastAPI()


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.pgpool = db.pool
    response = await call_next(request)
    return response


@app.on_event("startup")
async def startup():
    await db.create_pool()


@app.on_event("shutdown")
async def shutdown():
    await db.close()


@app.get("/users/me", response_model=UserProfile)
async def index(request: Request, token=Depends(ProtectedAny(scope=["users:free"]))):
    try:
        async with request.state.pgpool.acquire() as con:
            user_id = uuid.UUID(hex=token["userid"])
            rows = await con.fetchrow("select id, name, email, account_type, created_at, updated_at, data->'scope' as scope from users where id = $1", user_id)

            return UserProfile(
                username=rows.get("name", ""),
                email=rows.get("email", ""),
                user_id=rows.get("id","").hex if "id" in rows else "",
                account_type=rows.get("account_type", ""),
                scope=json.loads(rows.get("scope", "[]")),
            )
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/login", response_model=AccessToken)
async def login(request: Request, details: UserLogin):
    ph = PasswordHasher()
    failed_msg = "Username and/or password is incorrect"

    try:
        async with request.state.pgpool.acquire() as con:
            query = "SELECT password, id, data->'scope' as scope FROM users where deleted_at is null and name = $1"
            row = await con.fetchrow(query, details.username)

            try:
                ph.verify(row.get("password", "x"*100), details.password.get_secret_value())
            except VerifyMismatchError:
                raise LoginError(failed_msg)
            except InvalidHash:
                """
                  the user wasn't found but we don't want to leak info about valid users
                  through timing analysis so we still hash the supplied password before
                  returning an error
                """
                ph.hash(p)
                raise LoginError(failed_msg)
            else:
                scope = json.loads(row.get("scope", "[]"))
                jwt_token = create_token(scope=scope, userid=row["id"])
                return jwt_token

    except LoginError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.exception(f"login: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register(request: Request, details: UserCreate):
    ph = PasswordHasher()
    try:
        async with request.state.pgpool.acquire() as con:
            query = "select 1 from users where name = $1 or email = $2"
            exists = await con.fetch(query, details.username, details.email)

            async with con.transaction():
                # still hash even if user exists to avoid timing analysis leaks
                phash = ph.hash(details.password1.get_secret_value())

                if not exists:
                    data = {"scope": ["users:free"]}
                    insert = "INSERT INTO users (name, email, password, account_type, data) VALUES ($1, $2, $3, $4, $5) RETURNING id"
                    result = await con.fetchval(insert, details.username, details.email, phash, "free", json.dumps(data))

                    return UserProfile(
                        username=details.username,
                        email=details.email,
                        user_id=result.hex,
                        account_type="free",
                        scope=data["scope"],
                    )
                else:
                    raise RegistrationError("user registration failed")
    except RegistrationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
