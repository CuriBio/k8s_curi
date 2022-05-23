import logging
import json
from typing import Union
import uuid

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from asyncpg.exceptions import UniqueViolationError
from fastapi import FastAPI, Request, Depends, HTTPException, status

from auth import ProtectedAny, create_token
from core.db import Database
from models.errors import LoginError, RegistrationError
from models.tokens import LoginResponse
from models.users import UserLogin, UserCreate, UserProfile, CustomerProfile


logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

db = Database()
app = FastAPI(openapi_url=None)


CB_CUSTOMER_ID: uuid.UUID


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.pgpool = db.pool
    response = await call_next(request)
    return response


@app.on_event("startup")
async def startup():
    await db.create_pool()
    async with db.pool.acquire() as con:
        # might be a better way to do this without using global
        global CB_CUSTOMER_ID
        CB_CUSTOMER_ID = await con.fetchval("SELECT id FROM customers WHERE email = 'software@curibio.com'")


@app.on_event("shutdown")
async def shutdown():
    await db.close()


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


# TODO, could make details a Union of UserLogin and a new CustomerLogin model
@app.post("/login", response_model=LoginResponse)
async def login(request: Request, details: UserLogin):
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

    is_customer_login_attempt = details.customer_id is None

    if is_customer_login_attempt:
        query = (
            "SELECT password, id, data->'scope' AS scope "
            "FROM customers WHERE deleted_at IS NULL AND email = $1"
        )
        query_params = (details.username,)
    else:
        query = (
            "SELECT password, id, data->'scope' AS scope "
            "FROM users WHERE deleted_at IS NULL AND name = $1 AND customer_id = $2"
        )
        query_params = (details.username, details.customer_id)

    try:
        async with request.state.pgpool.acquire() as con:
            row = await con.fetchrow(query, *query_params)
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
                # TODO store the refresh token in the DB
                return LoginResponse(
                    access=create_token(scope=scope, userid=row["id"], refresh=False),
                    refresh=create_token(scope=scope, userid=row["id"], refresh=True),
                )

    except LoginError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.exception(f"login: Unexpected error {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# TODO, could make details a Union of UserCreate and a new CustomerCreate model
@app.post(
    "/register", response_model=Union[UserProfile, CustomerProfile], status_code=status.HTTP_201_CREATED
)
async def register(request: Request, details: UserCreate, token=Depends(ProtectedAny(scope=["users:admin"]))):
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

        is_customer_registration_attempt = customer_id == CB_CUSTOMER_ID and details.username is None
        register_type = "customer" if is_customer_registration_attempt else "user"
        logger.info(f"Attempting {register_type} registration")

        if is_customer_registration_attempt:
            insert_query = "INSERT INTO customers (email, password) VALUES ($1, $2) RETURNING id"
            scope = ["users:admin"]
            query_params = (details.email, phash)
        else:
            insert_query = (
                "INSERT INTO users (name, email, password, account_type, data, customer_id) "
                "VALUES ($1, $2, $3, $4, $5, $6) RETURNING id"
            )
            scope = ["users:free"]
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
