import logging
import json
from typing import Union
import uuid

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from asyncpg.exceptions import UniqueViolationError
from fastapi import FastAPI, Request, Depends, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from jwt.exceptions import InvalidTokenError

from auth import ProtectedAny, create_token, decode_token
from core.config import DATABASE_URL
from models.errors import LoginError, RegistrationError
from models.tokens import AuthTokens
from models.users import CustomerLogin, UserLogin, CustomerCreate, UserCreate, CustomerProfile, UserProfile
from utils.db import AsyncpgPoolDep


# logging is configured in log_config.yaml
logger = logging.getLogger(__name__)

asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)

app = FastAPI(openapi_url=None)

CB_CUSTOMER_ID: uuid.UUID

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dashboard.curibio-test.com",
        "https://dashboard.curibio.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.pgpool = await asyncpg_pool()
    response = await call_next(request)
    return response


@app.on_event("startup")
async def startup():
    pool = await asyncpg_pool()
    async with pool.acquire() as con:
        # might be a better way to do this without using global
        global CB_CUSTOMER_ID
        CB_CUSTOMER_ID = await con.fetchval("SELECT id FROM customers WHERE email = 'software@curibio.com'")


@app.get("/users/me", response_model=UserProfile)
async def index(request: Request, token=Depends(ProtectedAny(scope=["users:free"]))):
    try:
        async with request.state.pgpool.acquire() as con:
            user_id = uuid.UUID(hex=token["userid"])
            rows = await con.fetchrow(
                "select id, name, email, account_type, created_at, updated_at, data->'scope' as scope from users where id = $1",
                user_id,
            )

            return UserProfile(
                username=rows.get("name", ""),
                email=rows.get("email", ""),
                user_id=rows.get("id", "") if "id" in rows else "",
                account_type=rows.get("account_type", ""),
                scope=json.loads(rows.get("scope", "[]")),
            )
    except:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/login", response_model=AuthTokens)
async def login(request: Request, details: Union[UserLogin, CustomerLogin]):
    """Login a user or customer account.

    Logging in consists of validating the given credentials and, if valid,
    returning a JWT with the appropriate privileges.

    If no customer id is given, assume this is an attempt to login to a
    customer account which has admin privileges over its users, but cannot
    interact with any other services.

    Otherwise, attempt to login a regular user, which can interact with services
    like Pulse, Phenolearn, etc.
    """
    ph = PasswordHasher()
    failed_msg = "Invalid credentials"

    is_customer_login_attempt = type(details) is CustomerLogin

    if is_customer_login_attempt:
        account_type = "customer"
        select_query = (
            "SELECT password, id, data->'scope' AS scope "
            "FROM customers WHERE deleted_at IS NULL AND email = $1"
        )
        select_query_params = (details.email,)
        customer_id = None
    else:
        account_type = "user"
        select_query = (
            "SELECT password, id, data->'scope' AS scope "
            "FROM users WHERE deleted_at IS NULL AND name = $1 AND customer_id = $2"
        )
        select_query_params = (details.username, str(details.customer_id))
        customer_id = details.customer_id

    try:
        async with request.state.pgpool.acquire() as con:
            row = await con.fetchrow(select_query, *select_query_params)
            pw = details.password.get_secret_value()

            # if no record is returned by query then fetchrow will return None,
            # so need to set to a dict with a bad password hash
            if row is None:
                row = {"password": "x" * 100}

            try:
                # at this point, if no "password" key is present,
                # then there is an issue with the table in the database
                ph.verify(row["password"], pw)
            except VerifyMismatchError:
                raise LoginError(failed_msg)
            except InvalidHash:
                """
                The user or customer wasn't found but we don't want to leak info about valid users/customers
                through timing analysis so we still hash the supplied password before returning an error
                """
                ph.hash(pw)
                raise LoginError(failed_msg)
            else:
                scope = ["users:admin"] if is_customer_login_attempt else json.loads(row.get("scope", "[]"))
                return await _create_new_tokens(con, row["id"], customer_id, scope, account_type)

    except LoginError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.exception(f"login: Unexpected error {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/refresh", response_model=AuthTokens, status_code=status.HTTP_201_CREATED)
async def refresh(request: Request, token=Depends(ProtectedAny(refresh=True))):
    """Create a new access token and refresh token.

    The refresh token given in the request is first decoded and validated itself,
    then the refresh token stored in the DB for the user/customer making the request
    is decoded and validated, followed by checking that both tokens are the same.

    The value for the refresh token in the DB can either be null, an expired token, or a valid token.
    The client is considered logged out if the refresh token in the DB is null or expired and new tokens will
    not be generated in this case.

    In a successful request, the new refresh token will be stored in the DB for the given user/customer account
    """
    userid = uuid.UUID(hex=token["userid"])
    account_type = token["account_type"]

    if account_type == "customer":
        select_query = "SELECT refresh_token FROM customers WHERE id = $1"
    else:
        select_query = "SELECT refresh_token, customer_id FROM users WHERE id = $1"

    try:
        async with request.state.pgpool.acquire() as con:
            row = await con.fetchrow(select_query, userid)

            try:
                # decode and validate current refresh token
                current_token = decode_token(row["refresh_token"])
                # make sure the given token and the current token in the DB are the same
                assert token == current_token
            except (InvalidTokenError, AssertionError):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No authenticated user.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return await _create_new_tokens(con, userid, row.get("customer_id"), token["scope"], account_type)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"refresh: Unexpected error {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def _create_new_tokens(db_con, userid, customer_id, scope, account_type):
    # create new tokens
    access = create_token(
        userid=userid, customer_id=customer_id, scope=scope, account_type=account_type, refresh=False
    )
    refresh = create_token(
        userid=userid, customer_id=customer_id, scope=scope, account_type=account_type, refresh=True
    )

    # insert refresh token into DB
    if account_type == "customer":
        update_query = "UPDATE customers SET refresh_token = $1 WHERE id = $2"
    else:
        update_query = "UPDATE users SET refresh_token = $1 WHERE id = $2"

    await db_con.execute(update_query, refresh.token, userid)

    # return token model
    return AuthTokens(access=access, refresh=refresh)


@app.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(request: Request, token=Depends(ProtectedAny(check_scope=False))):
    """Logout the user/customer.

    The refresh token for the user/customer will be removed from the DB, so they will
    not be able to retrieve new tokens from /refresh. The only way to get new tokens at this point
    is through /login.

    This will not however affect their access token which will work fine until it expires.
    It is up to the client to discard the access token in order to truly logout the user.
    """
    userid = uuid.UUID(hex=token["userid"])
    if token["account_type"] == "customer":
        update_query = "UPDATE customers SET refresh_token = NULL WHERE id = $1"
    else:
        update_query = "UPDATE users SET refresh_token = NULL WHERE id = $1"

    try:
        async with request.state.pgpool.acquire() as con:
            await con.execute(update_query, userid)

    except Exception as e:
        logger.exception(f"logout: Unexpected error {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post(
    "/register", response_model=Union[UserProfile, CustomerProfile], status_code=status.HTTP_201_CREATED
)
async def register(
    request: Request,
    details: Union[CustomerCreate, UserCreate],
    token=Depends(ProtectedAny(scope=["users:admin"])),
):
    """Register a user or customer account.

    Only customer accounts with admin privileges can register users, and only the Curi Bio customer account
    can create new customers.

    If the customer ID in the auth token matches the Curi Bio Customer ID *AND* no username is given,
    assume this is an attempt to register a new customer account.

    Otherwise, attempt to register a regular user under the customer ID in the auth token

    **NOTE** there is currently no way to register a paid user, so all registered users will be created in
    the free tier until a way to designate the tier is specced out and added
    """
    ph = PasswordHasher()
    customer_id = uuid.UUID(hex=token["userid"])

    try:
        # still hash even if user or customer exists to avoid timing analysis leaks
        phash = ph.hash(details.password1.get_secret_value())
        
        is_customer_registration_attempt = customer_id == CB_CUSTOMER_ID and type(details) is CustomerCreate

        register_type = "customer" if is_customer_registration_attempt else "user"
        logger.info(f"Attempting {register_type} registration")

        if is_customer_registration_attempt:
            scope = ["users:admin"]
            insert_query = "INSERT INTO customers (email, password) VALUES ($1, $2) RETURNING id"
            query_params = (details.email, phash)
        else:
            scope = ["users:free"]
            insert_query = (
                "INSERT INTO users (name, email, password, account_type, data, customer_id) "
                "VALUES ($1, $2, $3, $4, $5, $6) RETURNING id"
            )
            query_params = (
                details.username,
                details.email,
                phash,
                "free",
                json.dumps({"scope": scope}),
                customer_id,
            )

        async with request.state.pgpool.acquire() as con:
            async with con.transaction():
                try:
                    result = await con.fetchval(insert_query, *query_params)
                except UniqueViolationError as e:
                    if "customers_email_key" in str(e):
                        # Returning this message is currently ok since only the Curi customer account
                        # can register other customers. Consider removing this message if the permissions are
                        # ever changed to allow people outside of Curi to register customer accounts
                        failed_msg = "Email already in use"
                    elif "users_customer_id_name_key" in str(e):
                        # Returning this message is currently ok since duplicate usernames are only
                        # disallowed if tied to the same customer account ID, so no info about users under
                        # other customer accounts will be leaked
                        failed_msg = "Username already in use"
                    elif "users_email_key" in str(e):
                        # Don't want to leak emails of users under other customer accounts, so return default msg
                        failed_msg = "Account registration failed"
                    else:
                        # default catch-all error message
                        failed_msg = "Account registration failed"
                    raise RegistrationError(failed_msg)

                if is_customer_registration_attempt:
                    return CustomerProfile(email=details.email, user_id=result.hex, scope=scope)
                else:
                    return UserProfile(
                        username=details.username,
                        email=details.email,
                        user_id=result.hex,
                        account_type="free",
                        scope=scope,
                    )

    except RegistrationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"register: Unexpected error {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
