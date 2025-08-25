import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from asyncpg.exceptions import UniqueViolationError
from fastapi import FastAPI, Request, Depends, HTTPException, status, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from jwt import decode, PyJWKClient
from jwt.exceptions import InvalidTokenError
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from starlette_context import context, request_cycle_context
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from uvicorn.protocols.utils import get_path_with_query_string

from auth import (
    ProtectedAny,
    create_token,
    decode_token,
    get_assignable_user_scopes,
    get_assignable_admin_scopes,
    get_scope_dependencies,
    validate_scope_dependencies,
    check_prohibited_user_scopes,
    check_prohibited_admin_scopes,
    convert_scope_str,
    ScopeTags,
    Scopes,
    DEFAULT_USAGE_LIMITS,
    ProhibitedScopeError,
    AuthTokens,
    get_account_scopes,
    create_new_tokens,
    AccountTypes,
    LoginType,
    get_product_tags_of_admin,
)
from jobs import check_customer_pulse3d_usage
from core.config import (
    DATABASE_URL,
    CURIBIO_EMAIL,
    CURIBIO_EMAIL_PASSWORD,
    DASHBOARD_URL,
    MICROSOFT_SSO_KEYS_URI,
    MICROSOFT_SSO_APP_ID,
    MICROSOFT_SSO_JWT_ALGORITHM,
)
from models.errors import LoginError, RegistrationError, EmailRegistrationError, UnableToUpdateAccountError
from models.users import (
    AdminLogin,
    UserLogin,
    SSOLogin,
    AdminCreate,
    UserCreate,
    AdminProfile,
    UserProfile,
    AccountUpdateAction,
    LoginResponse,
    PasswordModel,
    UserScopesUpdate,
    UnableToUpdateAccountResponse,
    PreferencesUpdate,
)
from utils.db import AsyncpgPoolDep
from utils.logging import setup_logger, bind_context_to_logger
from fastapi.templating import Jinja2Templates

setup_logger()
logger = structlog.stdlib.get_logger("api.access")

asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncpg_pool()
    yield


app = FastAPI(openapi_url=None, lifespan=lifespan)

MAX_FAILED_LOGIN_ATTEMPTS = 10
TEMPLATES = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[DASHBOARD_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next) -> Response:
    request.state.pgpool = await asyncpg_pool()

    # clear previous request variables
    clear_contextvars()
    # get request details for logging
    if (client_ip := request.headers.get("X-Forwarded-For")) is None:
        client_ip = f"{request.client.host}:{request.client.port}"

    url = get_path_with_query_string(request.scope)
    http_method = request.method
    http_version = request.scope["http_version"]
    start_time = time.perf_counter_ns()

    bind_contextvars(url=str(request.url), method=http_method, client_ip=client_ip)

    with request_cycle_context({}):
        response = await call_next(request)

        process_time = time.perf_counter_ns() - start_time
        status_code = response.status_code

        logger.info(
            f"""{client_ip} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
            status_code=status_code,
            duration=process_time / 10**9,
            **context,
        )

    return response


@app.post("/sso/admin", response_model=LoginResponse)
async def sso_admin(request: Request, details: SSOLogin):
    """SSO for an admin account.

    Logging in consists of validating the given credentials and, if valid,
    returning a JWT with the appropriate privileges.
    """
    id_token = await _decode_and_verify_jwt(details.id_token)
    email = id_token.get("email")
    if isinstance(email, str):
        email = email.lower()
    tid = id_token.get("tid")
    oid = id_token.get("oid")
    client_type = details.client_type if details.client_type else "unknown"

    bind_context_to_logger({"client_type": client_type, "email": email, "tid": tid, "oid": oid})

    logger.info(f"Admin SSO attempt from client '{client_type}'")

    try:
        async with request.state.pgpool.acquire() as con:
            select_query_result = await con.fetchrow(
                "SELECT id, suspended "
                "FROM customers "
                "WHERE deleted_at IS NULL AND LOWER(email)=$1 AND login_type!=$2 "
                "AND sso_organization=$3 AND sso_admin_org_id=$4",
                email,
                LoginType.PASSWORD,
                tid,
                oid,
            )

            if select_query_result is None:
                raise LoginError("Invalid credentials.")

            if select_query_result["suspended"]:
                raise LoginError(
                    "This account has been deactivated. Please contact Curi Bio to reactivate this account."
                )

            customer_id = select_query_result.get("id")
            bind_context_to_logger({"customer_id": str(customer_id)})

            login_response = await _build_admin_login_or_sso_response(
                con, customer_id, email, LoginType.SSO_MICROSOFT
            )
            return login_response
    except LoginError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception:
        logger.exception("POST /sso/admin: Unexpected error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error. Please try again later.",
        )


@app.post("/sso", response_model=LoginResponse)
async def sso_user(request: Request, details: SSOLogin):
    """SSO for a user account.

    Logging in consists of validating the given credentials and, if valid,
    returning a JWT with the appropriate privileges.
    """
    id_token = await _decode_and_verify_jwt(details.id_token)
    email = id_token.get("email")
    tid = id_token.get("tid")
    oid = id_token.get("oid")
    client_type = details.client_type if details.client_type else "unknown"

    bind_context_to_logger({"client_type": client_type, "email": email, "tid": tid, "oid": oid})

    logger.info(f"User SSO attempt from client '{client_type}'")

    try:
        async with request.state.pgpool.acquire() as con:
            select_query_result = await con.fetchrow(
                "SELECT u.id, u.suspended AS suspended, u.customer_id, c.suspended AS customer_suspended, "
                "u.verified, u.sso_user_org_id "
                "FROM users u JOIN customers c ON u.customer_id=c.id "
                "WHERE u.deleted_at IS NULL AND LOWER(u.email)=$1 AND u.login_type!=$2 AND c.sso_organization=$3",
                email,
                LoginType.PASSWORD,
                tid,
            )

            if select_query_result is None:
                raise LoginError("Invalid credentials.")

            if select_query_result["suspended"]:
                raise LoginError(
                    "This account has been deactivated. Please contact your administrator to reactivate this account."
                )

            if select_query_result["customer_suspended"]:
                raise LoginError("The customer ID for this account has been deactivated.")

            user_id = select_query_result.get("id")
            customer_id = select_query_result.get("customer_id")
            sso_user_org_id = select_query_result.get("sso_user_org_id")
            bind_context_to_logger({"customer_id": str(customer_id), "user_id": str(user_id)})

            if select_query_result["verified"]:
                if oid is not None and oid == sso_user_org_id:
                    # if sso was successful, then update last_login column value to now
                    await con.execute(
                        "UPDATE users SET last_login=$1 WHERE deleted_at IS NULL AND id=$2",
                        datetime.now(),
                        str(user_id),
                    )
                else:
                    raise LoginError("User organization id mismatch.")
            else:
                if sso_user_org_id is None and oid is not None:
                    # first sso attempt.  initialize the user's sso_user_org_id with the one in the incoming token
                    await con.execute(
                        "UPDATE users SET last_login=$1, sso_user_org_id=$2, verified='t' "
                        "WHERE deleted_at IS NULL AND id=$3",
                        datetime.now(),
                        str(oid),
                        str(user_id),
                    )
                else:
                    # user already has a sso_user_org_id value in the DB, or incoming token has no oid
                    raise LoginError("Bad user organization id state.")

            # get scopes from account_scopes table
            scopes = await get_account_scopes(con, customer_id, user_id)

            tokens = await create_new_tokens(
                con, user_id, customer_id, scopes, AccountTypes.USER, LoginType.SSO_MICROSOFT
            )
            return LoginResponse(tokens=tokens, usage_quota=None)
    except LoginError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception:
        logger.exception("POST /sso: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/login/admin", response_model=LoginResponse)
async def login_admin(request: Request, details: AdminLogin):
    """Login an admin account.

    Logging in consists of validating the given credentials and, if valid,
    returning a JWT with the appropriate privileges.

    If no customer id is given, assume this is an attempt to login to a
    admin account which has admin privileges over its users, but cannot
    interact with any other services.
    """
    account_type = AccountTypes.ADMIN
    email = details.email.lower()
    client_type = details.client_type if details.client_type else "unknown"

    bind_context_to_logger({"client_type": client_type, "email": email})

    logger.info(f"Admin login attempt from client '{client_type}'")

    try:
        async with request.state.pgpool.acquire() as con:
            select_query_result = await con.fetchrow(
                "SELECT password, id, failed_login_attempts, suspended "
                "FROM customers WHERE deleted_at IS NULL AND LOWER(email)=$1 AND login_type=$2",
                email,
                LoginType.PASSWORD,
            )

            # query will return None if customer email is not found
            # or if login_type is not "password"
            if select_query_result is None:
                customer_id = None
            else:
                customer_id = select_query_result.get("id")
                if select_query_result["password"] is None:
                    raise LoginError("Account needs verification")

            bind_context_to_logger({"customer_id": str(customer_id)})

            pw = details.password.get_secret_value()
            # verify password, else raise LoginError
            await _verify_password(con, account_type, pw, select_query_result)

            login_response = await _build_admin_login_or_sso_response(
                con, customer_id, email, LoginType.PASSWORD
            )
            return login_response

    except LoginError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception:
        logger.exception("POST /login/admin: Unexpected error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error. Please try again later.",
        )


@app.post("/login", response_model=LoginResponse)
async def login_user(request: Request, details: UserLogin):
    """Login a user account.

    Logging in consists of validating the given credentials and, if valid,
    returning a JWT with the appropriate privileges.
    """
    account_type = "user"
    username = details.username.lower()
    customer_id = details.customer_id
    user_id = None

    # select for service specific usage restrictions of the customer
    # suspended is for deactivated accounts and verified is for new users needing to verify through email

    # Tanner (7/25/23): need to use separate queries since asyncpg will raise an error if the value passed in to be compared against customer_id is not a UUID
    if isinstance(customer_id, uuid.UUID):
        # if a UUID was given in the request then check against the customer ID
        select_query = (
            "SELECT u.password, u.id, u.failed_login_attempts, u.suspended AS suspended, u.customer_id, c.suspended AS customer_suspended "
            "FROM users u JOIN customers c ON u.customer_id=c.id "
            "WHERE u.deleted_at IS NULL AND u.name=$1 AND u.customer_id=$2 AND u.verified='t' AND u.login_type=$3"
        )
    else:
        # if no UUID given, the check against the customer account alias
        # TODO should make sure an alias is actually set here?
        select_query = (
            "SELECT u.password, u.id, u.failed_login_attempts, u.suspended AS suspended, u.customer_id, c.suspended AS customer_suspended "
            "FROM users u JOIN customers c ON u.customer_id=c.id "
            "WHERE u.deleted_at IS NULL AND u.name=$1 AND c.alias IS NOT NULL AND LOWER(c.alias)=LOWER($2) AND u.verified='t' AND u.login_type=$3"
        )

    client_type = details.client_type if details.client_type else "unknown"

    bind_context_to_logger(
        {"customer_id": str(customer_id), "username": username, "client_type": client_type}
    )

    logger.info(f"User login attempt from client '{client_type}'")

    try:
        async with request.state.pgpool.acquire() as con:
            select_query_result = await con.fetchrow(
                select_query, username, str(details.customer_id), LoginType.PASSWORD
            )

            # query will return None if username is not found
            # or if login_type is not "password"
            if select_query_result is not None:
                user_id = select_query_result.get("id")
                customer_id = select_query_result.get("customer_id")
                # rebind customer id with uuid incase an alias was used above
                bind_context_to_logger({"customer_id": str(customer_id), "user_id": str(user_id)})

            pw = details.password.get_secret_value()

            # this will raise a LoginError if there are issues with the credentials or the user is suspended
            await _verify_password(con, account_type, pw, select_query_result)

            if select_query_result["customer_suspended"]:
                raise LoginError("The customer ID for this account has been deactivated.")

            # get scopes from account_scopes table
            scopes = await get_account_scopes(con, customer_id, user_id)

            # users logging into the dashboard should not have usage returned because they need to select a product from the landing page first to be given correct limits
            # users logging into a specific instrument need the the usage returned right away and it is known what instrument they are using
            usage_quota = None
            if (service := details.service) is not None:
                # TODO Luci (09/30/23): remove after all users upgrade to MA controller v1.2.2+, handling for pulse3d login types will no longer be needed
                service = service if service != "pulse3d" else "mantarray"
                usage_quota = await check_customer_pulse3d_usage(con, str(customer_id), service)

            # if login was successful, then update last_login column value to now
            # Tanner (7/25/23): using the customer ID returned from the select query since the customer ID field passed in with the request may contain an alias
            await con.execute(
                "UPDATE users SET last_login=$1, failed_login_attempts=0 "
                "WHERE deleted_at IS NULL AND name=$2 AND customer_id=$3 AND verified='t'",
                datetime.now(),
                username,
                str(customer_id),
            )

            tokens = await create_new_tokens(
                con, user_id, customer_id, scopes, account_type, LoginType.PASSWORD
            )

            return LoginResponse(tokens=tokens, usage_quota=usage_quota)

    except LoginError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception:
        logger.exception("POST /login: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def _build_admin_login_or_sso_response(con, customer_id, email, login_type: LoginType):
    # get scopes from account_scopes table
    scopes = await get_account_scopes(con, customer_id, None)

    # TODO split this part out into a new route
    # get list of scopes that the admin can assign to its users
    avail_user_scopes = get_assignable_user_scopes(scopes)
    user_scope_dependencies = get_scope_dependencies(avail_user_scopes)
    avail_admin_scopes = get_assignable_admin_scopes(scopes)
    admin_scope_dependencies = get_scope_dependencies(avail_admin_scopes)

    # TODO decide how to show admin accounts usage data for multiple products, defaulting to mantarray now
    # check usage for customer
    usage_quota = await check_customer_pulse3d_usage(con, str(customer_id), "mantarray")

    # if login was successful, then update last_login column value to now
    await con.execute(
        "UPDATE customers SET last_login=$1, failed_login_attempts=0 WHERE deleted_at IS NULL AND LOWER(email)=LOWER($2)",
        datetime.now(),
        email,
    )

    tokens = await create_new_tokens(con, None, customer_id, scopes, AccountTypes.ADMIN, login_type)

    # TODO fix tests for this?
    return LoginResponse(
        tokens=tokens,
        usage_quota=usage_quota,
        user_scopes=user_scope_dependencies,
        admin_scopes=admin_scope_dependencies,
    )


async def _decode_and_verify_jwt(token):
    client = PyJWKClient(MICROSOFT_SSO_KEYS_URI)
    signing_key = client.get_signing_key_from_jwt(token)
    payload = decode(
        token, signing_key.key, algorithms=[MICROSOFT_SSO_JWT_ALGORITHM], audience=MICROSOFT_SSO_APP_ID
    )
    return payload


async def _verify_password(con, account_type, pw, select_query_result) -> None:
    ph = PasswordHasher()

    invalid_creds_msg = "Invalid credentials. Account will be locked after 10 failed attempts."
    account_locked_msg = "Account locked. Too many failed attempts."
    deactivated_msg = (
        "This account has been deactivated. Please contact your administrator to reactivate this account."
        if account_type == "user"
        else "This account has been deactivated. Please contact Curi Bio to reactivate this account."
    )

    if select_query_result is None:
        # if no record is returned by query then fetchrow will return None,
        # so need to set to a dict with a bad password hash
        select_query_result = {"password": "x" * 100}

    try:
        # at this point, if no "password" key is present,
        # then there is an issue with the table in the database
        ph.verify(select_query_result["password"], pw)
    except VerifyMismatchError:
        # first check if account is already locked
        # should never be greater than maximum, but handling in case
        if select_query_result["failed_login_attempts"] >= MAX_FAILED_LOGIN_ATTEMPTS:
            raise LoginError(account_locked_msg)

        # increment admin/user failed attempts
        updated_failed_attempts = select_query_result["failed_login_attempts"] + 1
        logger.info(
            f"Failed login attempt {updated_failed_attempts} for {account_type} id: {select_query_result['id']}"
        )
        await _update_failed_login_attempts(
            con, account_type, select_query_result["id"], updated_failed_attempts
        )
        # update login error if this failed attempt hits limit
        raise LoginError(
            account_locked_msg if updated_failed_attempts == MAX_FAILED_LOGIN_ATTEMPTS else invalid_creds_msg
        )
    except InvalidHash:
        """
        The user or admin wasn't found but we don't want to leak info about valid users/admins
        through timing analysis so we still hash the supplied password before returning an error
        """
        ph.hash(pw)
        raise LoginError(invalid_creds_msg)
    else:
        # only raise LoginError here when account is locked on successful creds after they have been checked to prevent giving away facts about successful login combinations
        if select_query_result["failed_login_attempts"] >= MAX_FAILED_LOGIN_ATTEMPTS:
            raise LoginError(account_locked_msg)
        # user can be suspended if admin account suspends them, select_query_result will not return None in that instance
        if select_query_result["suspended"]:
            raise LoginError(deactivated_msg)


async def _update_failed_login_attempts(con, account_type: str, id: str, count: int) -> None:
    account_type_table = f"{account_type if account_type == 'user' else 'customer'}s"

    if count == MAX_FAILED_LOGIN_ATTEMPTS:
        # if max failed attempts is reached, then deactivate the account and increment count
        update_query = f"UPDATE {account_type_table} SET suspended='t', failed_login_attempts=failed_login_attempts+1 where id=$1"
    else:
        # else increment failed attempts
        update_query = (
            f"UPDATE {account_type_table} SET failed_login_attempts=failed_login_attempts+1 where id=$1"
        )

    await con.execute(update_query, id)


async def _update_password(con, pw, previous_passwords, update_query, query_params):
    ph = PasswordHasher()
    phash = ph.hash(pw)
    # make sure new password does not match any previous passwords on file
    for prev_pw in previous_passwords:
        try:
            ph.verify(prev_pw, pw)
        except VerifyMismatchError:
            # passwords don't match, nothing else to do
            continue
        else:
            # passwords match, return msg indicating that this is the case
            raise UnableToUpdateAccountError()

    await con.execute(update_query, phash, *query_params)


@app.post("/refresh", response_model=AuthTokens, status_code=status.HTTP_201_CREATED)
async def refresh(request: Request, token=Depends(ProtectedAny(scopes=[Scopes.REFRESH]))):
    """Create a new access token and refresh token.

    The refresh token given in the request is first decoded and validated itself,
    then the refresh token stored in the DB for the user/admin making the request
    is decoded and validated, followed by checking that both tokens are the same.

    The value for the refresh token in the DB can either be null, an expired token, or a valid token.
    The client is considered logged out if the refresh token in the DB is null or expired and new tokens will
    not be generated in this case.

    In a successful request, the new refresh token will be stored in the DB for the given user/admin account
    """
    account_id = uuid.UUID(hex=token.account_id)
    account_type = token.account_type
    login_type = token.login_type
    is_admin_account = account_type == AccountTypes.ADMIN

    bind_context_to_logger({"customer_id": token.customer_id, "user_id": token.userid})

    if is_admin_account:
        select_query = "SELECT refresh_token FROM customers WHERE id=$1"
    else:
        select_query = "SELECT refresh_token, customer_id FROM users WHERE id=$1"

    try:
        async with request.state.pgpool.acquire() as con:
            row = await con.fetchrow(select_query, account_id)

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

            user_id = None if is_admin_account else account_id
            customer_id = account_id if is_admin_account else row["customer_id"]
            scopes = await get_account_scopes(con, customer_id, user_id)

            # con is passed to this function, so it must be inside this async with block
            return await create_new_tokens(con, user_id, customer_id, scopes, account_type, login_type)

    except HTTPException:
        raise
    except Exception:
        logger.exception("POST /refresh: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(request: Request, token=Depends(ProtectedAny(scopes=list(Scopes)))):
    """Logout the user/admin.

    The refresh token for the user/admin will be removed from the DB, so they will
    not be able to retrieve new tokens from /refresh. The only way to get new tokens at this point
    is through /login.

    This will not however affect their access token which will work fine until it expires.
    It is up to the client to discard the access token in order to truly logout the user.
    """
    account_id = uuid.UUID(hex=token.account_id)
    is_admin_account = token.account_type == AccountTypes.ADMIN

    bind_context_to_logger({"customer_id": token.customer_id, "user_id": str(account_id)})

    if is_admin_account:
        update_query = "UPDATE customers SET refresh_token = NULL WHERE id=$1"
    else:
        update_query = "UPDATE users SET refresh_token = NULL WHERE id=$1"

    try:
        async with request.state.pgpool.acquire() as con:
            await con.execute(update_query, account_id)

    except Exception:
        logger.exception("POST /logout: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/register/admin", response_model=AdminProfile, status_code=status.HTTP_201_CREATED)
async def register_admin(
    request: Request, details: AdminCreate, token=Depends(ProtectedAny(scopes=[Scopes.CURI__ADMIN]))
):
    """Register an admin account for a new customer.

    Only the Curi Bio root account can create new admins.
    """
    try:
        email = details.email.lower()
        login_type = details.login_type
        sso_organization = details.sso_organization
        sso_admin_org_id = details.sso_admin_org_id

        if login_type == LoginType.PASSWORD and (
            sso_organization is not None or sso_admin_org_id is not None
        ):
            raise RegistrationError(
                "Password-based accounts should not send sso_organization or sso_admin_org_id"
            )

        if login_type != LoginType.PASSWORD and (sso_organization is None or sso_admin_org_id is None):
            raise RegistrationError("SSO accounts require sso_organization and sso_admin_org_id")

        check_prohibited_admin_scopes(details.scopes, token.scopes)
        validate_scope_dependencies(details.scopes)

        async with request.state.pgpool.acquire() as con:
            async with con.transaction():
                try:
                    insert_account_query_args = (
                        "INSERT INTO customers (email, usage_restrictions, login_type, sso_organization, sso_admin_org_id) "
                        "VALUES ($1, $2, $3, $4, $5) RETURNING id",
                        email,
                        json.dumps(dict(DEFAULT_USAGE_LIMITS)),
                        login_type,
                        sso_organization,
                        sso_admin_org_id,
                    )
                    new_account_id = await con.fetchval(*insert_account_query_args)
                    bind_context_to_logger({"customer_id": str(new_account_id), "email": email})
                except UniqueViolationError as e:
                    if "customers_email_key" in str(e):
                        # Returning this message is currently ok since only the Curi root account
                        # can register other admins. Consider removing this message if the permissions are
                        # ever changed to allow people outside of Curi to register admin accounts
                        failed_msg = "Email already in use"
                    else:
                        # default catch-all error message
                        failed_msg = "Customer registration failed"
                    raise RegistrationError(failed_msg)

                # add scope for new account
                insert_scope_query_args = (new_account_id, details.scopes)
                await con.execute(
                    "INSERT INTO account_scopes VALUES ($1, NULL, unnest($2::text[]))",
                    *insert_scope_query_args,
                )

                # only send verification emails to new users
                if login_type == LoginType.PASSWORD:  # Username / Password path
                    await _create_account_email(
                        con=con,
                        action="verify",
                        user_id=None,
                        customer_id=new_account_id,
                        scope=Scopes.ADMIN__VERIFY,
                        name=None,
                        email=email,
                    )
                else:  # SSO path
                    template_body = {"username": "Admin", "url": f"{DASHBOARD_URL}"}
                    await _send_account_email(
                        emails=[email],
                        subject="Your Admin account has been created",
                        template="registration_sso.html",
                        template_body=template_body,
                    )

                return AdminProfile(email=email, user_id=new_account_id.hex, scopes=details.scopes)

    except (RegistrationError, ProhibitedScopeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception("POST /register/admin: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/register/user", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: Request, details: UserCreate, token=Depends(ProtectedAny(tag=ScopeTags.ADMIN))
):
    """Register a user account.

    Only admin accounts can register users.
    """
    customer_id = uuid.UUID(hex=token.customer_id)
    admin_scopes = token.scopes
    user_scopes = details.scopes
    try:
        email = details.email.lower()
        username = details.username.lower()

        bind_context_to_logger({"customer_id": str(customer_id), "username": username, "email": email})
        check_prohibited_user_scopes(user_scopes, admin_scopes)
        validate_scope_dependencies(user_scopes)

        logger.info(f"Registering new user with scopes: {user_scopes}")

        async with request.state.pgpool.acquire() as con:
            async with con.transaction():
                try:
                    select_customer_login_type_query = (
                        "SELECT login_type FROM customers WHERE id=$1",
                        customer_id,
                    )
                    customer_login_type = await con.fetchval(*select_customer_login_type_query)

                    # suspended and verified get set to False by default
                    insert_account_query_args = (
                        "INSERT INTO users (name, email, customer_id, login_type) "
                        "VALUES ($1, $2, $3, $4) RETURNING id",
                        username,
                        email,
                        customer_id,
                        customer_login_type,
                    )

                    new_account_id = await con.fetchval(*insert_account_query_args)
                    bind_context_to_logger({"user_id": str(new_account_id)})
                except UniqueViolationError as e:
                    if "users_customer_id_name_key" in str(e):
                        # Returning this message is currently ok since duplicate usernames are only
                        # disallowed if tied to the same customer account ID, so no info about users under
                        # other customer accounts will be leaked
                        failed_msg = "Username already in use"
                    elif "users_email_key" in str(e):
                        failed_msg = "Email already in use"
                    else:
                        # default catch-all error message
                        failed_msg = "Account registration failed"
                    raise RegistrationError(failed_msg)

                # add scope for new account
                insert_scope_query_args = (customer_id, new_account_id, user_scopes)
                await con.execute(
                    "INSERT INTO account_scopes VALUES ($1, $2, unnest($3::text[]))", *insert_scope_query_args
                )

                # only send verification emails to new users
                if customer_login_type == LoginType.PASSWORD:  # Username / Password path
                    await _create_account_email(
                        con=con,
                        action="verify",
                        user_id=new_account_id,
                        customer_id=customer_id,
                        scope=Scopes.USER__VERIFY,
                        name=username,
                        email=email,
                    )
                else:  # SSO path
                    template_body = {"username": username, "url": f"{DASHBOARD_URL}"}
                    await _send_account_email(
                        emails=[email],
                        subject="Your User account has been created",
                        template="registration_sso.html",
                        template_body=template_body,
                    )

                return UserProfile(
                    username=username, email=email, user_id=new_account_id.hex, scopes=user_scopes
                )

    except (EmailRegistrationError, ProhibitedScopeError, RegistrationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception("POST /register: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/email", status_code=status.HTTP_204_NO_CONTENT)
async def email_account(
    request: Request, email: EmailStr = Query(None), action: str = Query(None), user: bool = Query(None)
):
    """Send or resend account emails.

    No token required for request. Currently sending reset password and new registration emails based on query type.
    """
    email = email.lower()
    try:
        async with request.state.pgpool.acquire() as con:
            query = (
                "SELECT id, customer_id, name FROM users WHERE LOWER(email)=$1 AND login_type=$2"
                if user
                else "SELECT id FROM customers WHERE LOWER(email)=$1 AND login_type=$2"
            )

            row = await con.fetchrow(query, email, LoginType.PASSWORD)

            # send email if found and password-based user, otherwise return 204, doesn't need to raise an exception
            if row is None:
                logger.info(f"No account found with email address '{email}'")
                return

            if user:
                user_id = row["id"]
                customer_id = row["customer_id"]
                username = row["name"]
            else:
                user_id = None
                customer_id = row["id"]
                username = None

            bind_context_to_logger(
                {"user_id": str(user_id), "customer_id": str(customer_id), "username": username}
            )
            scope = convert_scope_str(f"{'user' if user else 'admin'}:{action}")

            await _create_account_email(
                con=con,
                action=action,
                user_id=user_id,
                customer_id=customer_id,
                scope=scope,
                name=username,
                email=email,
            )

    except Exception:
        logger.exception("GET /email: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def _create_account_email(
    *,
    con,
    action: str,
    user_id: uuid.UUID | None,
    customer_id: uuid.UUID,
    scope: Scopes,
    name: str | None,
    email: EmailStr,
):
    try:
        if ScopeTags.ACCOUNT not in scope.tags:
            raise Exception(f"Scope {scope} is not allowed in an email token")

        if "user" in scope:
            account_type = AccountTypes.USER
            account_id = user_id
            table = "users"
        else:
            account_type = AccountTypes.ADMIN
            account_id = customer_id
            table = "customers"

        query = f"UPDATE {table} SET reset_token=$1 WHERE id=$2"

        # create email verification token, exp 24 hours
        jwt_token = create_token(
            userid=user_id, customer_id=customer_id, scopes=[scope], account_type=account_type
        )

        url = f"{DASHBOARD_URL}/account/{action}?token={jwt_token.token}"

        # assign correct email template and redirect url based on request type
        if action == "reset":
            subject = "Reset your password"
            template = "reset_password.html"
        elif action == "verify":
            subject = "Please verify your email address"
            template = "registration.html"
        else:
            logger.error(f"{action} is not a valid action allowed in this request")
            raise Exception()

        # add token to users table after no exception is raised
        # The token  has to be created with id being returned from insert query so it's updated separately
        await con.execute(query, jwt_token.token, account_id)

        # send email with reset token
        template_body = {"username": name, "url": url}
        await _send_account_email(
            emails=[email], subject=subject, template=template, template_body=template_body
        )
    except Exception as e:
        raise EmailRegistrationError(e)


async def _send_account_email(
    *, emails: list[EmailStr], subject: str, template: str, template_body: dict
) -> None:
    logger.info(f"Sending email with subject '{subject}' to email addresses '{emails}'")

    conf = ConnectionConfig(
        MAIL_USERNAME=CURIBIO_EMAIL,
        MAIL_PASSWORD=CURIBIO_EMAIL_PASSWORD,
        MAIL_FROM=CURIBIO_EMAIL,
        MAIL_PORT=587,
        MAIL_SERVER="smtp.gmail.com",
        MAIL_FROM_NAME="Curi Bio Team",
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        TEMPLATE_FOLDER="./templates",
    )

    if template_body.get("username") is None:
        template_body["username"] = "Admin"

    message = MessageSchema(
        subject=subject,
        recipients=emails,
        subtype=MessageType.html,
        template_body=template_body,
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name=template)


@app.put("/account")
async def update_accounts(
    request: Request, details: PasswordModel, token=Depends(ProtectedAny(tag=ScopeTags.ACCOUNT))
):
    """Confirm and verify new user and password.

    Used for both resetting new password or verifying new user accounts. Route will check if the token has been used or if account has already been verified.
    """
    try:
        account_id = uuid.UUID(hex=token.account_id)
        customer_id = uuid.UUID(hex=token.customer_id)

        bind_context_to_logger({"customer_id": token.customer_id, "user_id": token.userid})

        is_admin = token.account_type == AccountTypes.ADMIN
        is_user = not is_admin

        pw = details.password1.get_secret_value()

        async with request.state.pgpool.acquire() as con:
            async with con.transaction():
                # ProtectedAny will return 401 already if token has expired, so no need to check again

                # get necessary info from DB before making any changes or validating any data
                query = (
                    "SELECT reset_token, previous_passwords FROM customers WHERE id=$1"
                    if is_admin
                    else "SELECT verified, reset_token, previous_passwords FROM users WHERE id=$1 AND customer_id=$2"
                )
                query_params = [account_id]
                if is_user:
                    query_params.append(customer_id)

                row = await con.fetchrow(query, *query_params)

                # if the token is being used to verify the user account and the account has already been verified, then return message to display to user
                if is_user and details.verify and row["verified"]:
                    msg = "Account has already been verified"
                    logger.error(f"PUT /account: {msg}")
                    return UnableToUpdateAccountResponse(message=msg)
                # token in db gets replaced with NULL when it's been successfully used
                if row["reset_token"] is None:
                    msg = "Link has already been used"
                    logger.error(f"PUT /account: {msg}")
                    return UnableToUpdateAccountResponse(message=msg)

                # if there is a token present in the DB but it does not match the one provided to this route, then presumably a new one has been created and thus the one being used should be considered expired
                try:
                    # decode and validate current reset token
                    current_token = decode_token(row["reset_token"])
                    # make sure the given token and the current token in the DB are the same
                    assert token == current_token
                except (InvalidTokenError, AssertionError):
                    msg = "Link has expired"
                    logger.error(f"PUT /account: {msg}")
                    return UnableToUpdateAccountResponse(message=msg)

                # Update the password of the account, and if it is a user also set the account as verified
                update_query = (
                    "UPDATE customers SET reset_token=NULL, password=$1, previous_passwords=array_prepend($1, previous_passwords[0:4]) WHERE id=$2"
                    if is_admin
                    else "UPDATE users SET verified='t', reset_token=NULL, password=$1, previous_passwords=array_prepend($1, previous_passwords[0:4]) WHERE id=$2 AND customer_id=$3"
                )
                query_params = [account_id]

                if is_user:
                    query_params.append(customer_id)

                await _update_password(con, pw, row["previous_passwords"], update_query, query_params)

    except UnableToUpdateAccountError:
        msg = "Cannot set password to any of the previous 5 passwords"
        logger.error(f"PUT /account: {msg}")
        return UnableToUpdateAccountResponse(message=msg)
    except HTTPException:
        raise
    except Exception:
        logger.exception("PUT /account: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/")
async def get_all_users(request: Request, token=Depends(ProtectedAny(tag=ScopeTags.ADMIN))):
    """Get info for all the users under the given admin account.

    List of users returned will be sorted with all active users showing up first, then all the suspended (deactivated) users
    """
    customer_id = uuid.UUID(hex=token.customer_id)

    bind_context_to_logger({"customer_id": str(customer_id), "user_id": None})

    query = (
        "SELECT u.id, u.name, u.email, u.created_at, u.last_login, u.verified, "
        "u.suspended, u.login_type, u.reset_token, array_agg(s.scope) as scopes "
        "FROM users u "
        "LEFT JOIN account_scopes s ON u.id=s.user_id "
        "WHERE u.customer_id=$1 AND u.deleted_at IS NULL "
        "GROUP BY u.id, u.name, u.email, u.created_at, u.last_login, u.verified, "
        "u.suspended, u.login_type, u.reset_token "
        "ORDER BY u.suspended"
    )

    try:
        async with request.state.pgpool.acquire() as con:
            result = await con.fetch(query, customer_id)

        formatted_results = [dict(row) for row in result]

        for row in formatted_results:
            # unverified account should have a jwt token, otherwise will be None.
            # check expiration and if expired, return it as None, FE will handle telling user it's expired
            try:
                decode_token(row["reset_token"])
            except Exception:
                row["reset_token"] = None

        return formatted_results

    except Exception:
        logger.exception("GET /: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/customers")
async def get_all_customers(request: Request, token=Depends(ProtectedAny(scopes=[Scopes.CURI__ADMIN]))):
    """Get info for all the customer accounts.

    List of customers returned will be sorted with all active customer showing up first, then all the suspended (deactivated) customer.
    """
    customer_id = uuid.UUID(hex=token.customer_id)

    bind_context_to_logger({"customer_id": str(customer_id), "user_id": None})

    query = (
        "SELECT c.id, c.email, c.last_login, c.suspended, c.usage_restrictions, array_agg(s.scope) as scopes "
        "FROM customers c "
        "LEFT JOIN account_scopes s ON c.id=s.customer_id "
        "WHERE s.user_id IS NULL AND c.id!=$1"  # don't return curi customer account
        "GROUP BY c.id, c.email, c.last_login, c.suspended, c.usage_restrictions "
        "ORDER BY c.suspended"
    )

    try:
        async with request.state.pgpool.acquire() as con:
            result = await con.fetch(query, customer_id)

        return [dict(row) for row in result]

    except Exception:
        logger.exception("GET /: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# TODO could be added to PUT /{account_id}
@app.put("/scopes/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_scopes(
    request: Request,
    details: UserScopesUpdate,
    account_id: uuid.UUID,
    token=Depends(ProtectedAny(tag=ScopeTags.ADMIN)),
):
    """Update a user's scopes in the database."""
    customer_id = uuid.UUID(hex=token.customer_id)
    admin_scopes = token.scopes
    updated_user_scopes = details.scopes

    bind_context_to_logger({"customer_id": str(customer_id), "user_id": str(account_id)})

    try:
        check_prohibited_user_scopes(updated_user_scopes, admin_scopes)
        validate_scope_dependencies(updated_user_scopes)

        async with request.state.pgpool.acquire() as con:
            async with con.transaction():
                # The update will include all scopes that should be assigned after this operation, so first
                # delete existing scopes from database and then insert the updated scopes
                await con.execute(
                    "DELETE FROM account_scopes WHERE customer_id=$1 AND user_id=$2", customer_id, account_id
                )
                await con.execute(
                    "INSERT INTO account_scopes VALUES ($1, $2, unnest($3::text[]))",
                    customer_id,
                    account_id,
                    updated_user_scopes,
                )
    except ProhibitedScopeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception(f"PUT /scopes/{account_id}: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/preferences")
async def get_user_preferences(request: Request, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE))):
    """Get preferences for user."""
    user_id = uuid.UUID(token.userid)
    bind_context_to_logger({"customer_id": token.customer_id, "user_id": str(user_id)})

    try:
        async with request.state.pgpool.acquire() as con:
            query = "SELECT preferences FROM users WHERE id=$1"
            row = await con.fetchrow(query, user_id)
            return json.loads(row["preferences"])
    except Exception:
        logger.exception("GET /: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.put("/preferences")
async def update_user_preferences(
    request: Request, details: PreferencesUpdate, token=Depends(ProtectedAny(tag=ScopeTags.PULSE3D_WRITE))
):
    """Update a user's product preferences."""
    user_id = uuid.UUID(token.userid)
    bind_context_to_logger(
        {
            "customer_id": token.customer_id,
            "user_id": str(user_id),
            "product": details.product,
            "preferences": details.changes,
        }
    )

    try:
        async with request.state.pgpool.acquire() as con:
            query = "UPDATE users SET preferences=jsonb_set(preferences, $1, $2) WHERE id=$3 RETURNING preferences"
            row = await con.fetchrow(query, {details.product}, json.dumps(details.changes), user_id)
            # return new preferences because service worker caches both GET and POST so return value needs to be the same format
            return json.loads(row["preferences"])
    except Exception:
        logger.exception("PUT /preferences: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Luci (10/5/22) Following two routes need to be last otherwise will mess with the ProtectedAny scope used in Auth
# Please see https://fastapi.tiangolo.com/tutorial/path-params/#order-matters
@app.get("/{account_id}")
async def get_user(
    request: Request,
    account_id: uuid.UUID,
    # TODO consider changing how this is scoped
    token=Depends(ProtectedAny(scopes=[s for s in Scopes if ScopeTags.ACCOUNT not in s.tags])),
):
    """Get info for the account with the given ID.

    If the account is a user account, the ID must exist under the customer ID in the token
    """
    self_id = uuid.UUID(hex=token.account_id)
    is_admin_account = token.account_type == AccountTypes.ADMIN
    is_self_retrieval = self_id == account_id

    get_user_info_query = (
        "SELECT id, name, email, created_at, last_login, suspended FROM users "
        "WHERE customer_id=$1 AND id=$2 AND deleted_at IS NULL"
    )

    if is_admin_account:
        if is_self_retrieval:
            query = "SELECT id, created_at, alias FROM customers WHERE id=$1"
            query_args = (self_id,)
        else:
            # assume that account ID is a user ID since no admin account can retrieve details of another
            query = get_user_info_query
            query_args = (self_id, account_id)

        # this is only being set in case an error is raised later
        customer_id = self_id
        bind_context_to_logger({"user_id": str(account_id), "customer_id": str(customer_id)})
    else:
        if not is_self_retrieval:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User accounts cannot retrieve details of other accounts",
            )

        customer_id = uuid.UUID(hex=token.customer_id)
        bind_context_to_logger({"user_id": str(self_id), "customer_id": str(customer_id)})

        query = get_user_info_query
        query_args = (customer_id, account_id)

    try:
        async with request.state.pgpool.acquire() as con:
            row = await con.fetchrow(query, *query_args)

        if not row:
            if is_admin_account and self_id == account_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error retrieving admin account details",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User ID: {account_id} not found under Customer ID: {customer_id}",
                )

        return dict(row)

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"GET /{account_id}: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.put("/customers/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_customer(
    request: Request,
    details: AccountUpdateAction,
    account_id: uuid.UUID,
    token=Depends(ProtectedAny(scopes=[Scopes.CURI__ADMIN])),
):
    """Update a customer account's information in the database, restricted use for Curi Admin.

    The action to take on the user should be passed in the body of PUT request as action_type:
        - deactivate: set suspended field to true
        - reactivate: set sespended field to false and set login attempts to 0
        - edit:
            - update usage restrictions
            - update account scopes for customer (if removing a scope, it will remove the dependent scopes from users under that customer as well)
    """
    self_id = uuid.UUID(hex=token.account_id)
    action = details.action_type
    email_content = {}

    try:
        bind_context_to_logger(
            {
                "user_id": None,
                "customer_id": str(self_id),
                "action": action,
                "target_customer": str(account_id),
            }
        )

        async with request.state.pgpool.acquire() as con:
            async with con.transaction():
                if action == "deactivate":
                    await con.execute("UPDATE customers SET suspended='t' WHERE id=$1", account_id)
                elif action == "reactivate":
                    # when reactivated, failed login attempts should be set back to 0.
                    await con.execute(
                        "UPDATE customers SET suspended='f', failed_login_attempts=0 WHERE id=$1", account_id
                    )
                elif action == "edit":
                    # snapshot 'before' state
                    usage_restrictions_query = "SELECT email, usage_restrictions FROM customers WHERE id=$1"
                    usage_restrictions_query_result = await con.fetchrow(usage_restrictions_query, account_id)
                    customer_email = usage_restrictions_query_result["email"]
                    current_usage_restrictions = json.loads(
                        usage_restrictions_query_result["usage_restrictions"]
                    )
                    current_products = get_product_tags_of_admin(
                        await get_account_scopes(con, account_id, None)
                    )

                    # handle usage restrictions updates
                    if (usage_restrictions_update := details.usage) is not None:
                        # TODO validate the new usage restrictions?
                        await con.execute(
                            "UPDATE customers SET usage_restrictions=$1 WHERE id=$2",
                            json.dumps(usage_restrictions_update),
                            account_id,
                        )

                    # handle product scope updates
                    if (updated_scopes := details.scopes) is not None:
                        check_prohibited_admin_scopes(updated_scopes, token.scopes)
                        validate_scope_dependencies(updated_scopes)

                        updated_products = get_product_tags_of_admin(updated_scopes)
                        # if a product has been completely removed from an admin account, then remove all customer and user entries from account_scopes
                        if products_removed := set(current_products) - set(updated_products):
                            for product in products_removed:
                                await con.execute(
                                    "DELETE FROM account_scopes WHERE customer_id=$1 AND scope LIKE $2",
                                    account_id,
                                    f"{product}%",
                                )
                        # The update will include all scopes that should be assigned after this operation, so first
                        # delete existing scopes from database and then insert the updated scopes
                        await con.execute(
                            "DELETE FROM account_scopes WHERE customer_id=$1 AND user_id IS NULL", account_id
                        )
                        await con.execute(
                            "INSERT INTO account_scopes VALUES ($1, NULL, unnest($2::text[]))",
                            account_id,
                            [str(s) for s in updated_scopes],
                        )

                    # capture 'after' state
                    usage_restrictions_query_result = await con.fetchrow(usage_restrictions_query, account_id)
                    updated_usage_restrictions = json.loads(
                        usage_restrictions_query_result["usage_restrictions"]
                    )
                    updated_products = get_product_tags_of_admin(
                        await get_account_scopes(con, account_id, None)
                    )

                    # prepare email_content
                    email_content["email"] = customer_email
                    email_content["current"] = {
                        "usage_restrictions": current_usage_restrictions,
                        "products": current_products,
                    }
                    email_content["updated"] = {
                        "usage_restrictions": updated_usage_restrictions,
                        "products": updated_products,
                    }
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid curi-edit-admin action: {action}",
                    )
        if email_content:
            template_body = {
                "before": _get_pretty_admin_details(email_content["current"]),
                "after": _get_pretty_admin_details(email_content["updated"]),
            }
            await _send_account_email(
                emails=[email_content["email"], "support@curibio.com"],
                subject="Your Admin account has been modified",
                template="admin_modified.html",
                template_body=template_body,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"PUT /customers/{account_id}: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _get_pretty_admin_details(details):
    result = {}

    for product in sorted(details["products"]):
        if product in details["usage_restrictions"]:
            usage_restrictions = details["usage_restrictions"][product]
            product_result = {}

            if "jobs" in usage_restrictions:
                product_result["jobs"] = (
                    "unlimited" if usage_restrictions["jobs"] == -1 else usage_restrictions["jobs"]
                )

            if "uploads" in usage_restrictions:
                product_result["uploads"] = (
                    "unlimited" if usage_restrictions["uploads"] == -1 else usage_restrictions["uploads"]
                )

            if "expiration_date" in usage_restrictions:
                product_result["expiration_date"] = (
                    "none"
                    if usage_restrictions["expiration_date"] is None
                    else usage_restrictions["expiration_date"]
                )

            if product_result:
                result[product.value] = product_result

    return result


@app.put("/{account_id}")
async def update_account(
    request: Request,
    details: AccountUpdateAction,
    account_id: uuid.UUID,
    # TODO consider changing how this is scoped
    token=Depends(ProtectedAny(scopes=[s for s in Scopes if ScopeTags.ACCOUNT not in s.tags])),
):
    """Update an account's information in the database.

    There are three classes of actions that can be taken:
        - an admin account updating one of its user accounts
        - an admin account updating itself
        - a user account updating itself

    The action to take on the user should be passed in the body of PUT request as action_type:
        - deactivate (admin->user): set suspended field to true
        - delete (admin->user): set deleted_at field to current time
        - set_alias (admin->self): set the alias field to the given value
        - set_password (admin->self, user->self): change user/admin password
    """
    self_id = uuid.UUID(hex=token.account_id)
    action = details.action_type

    is_admin_account = token.account_type == AccountTypes.ADMIN
    is_user_account = token.account_type == AccountTypes.USER
    is_self_edit = self_id == account_id

    # TODO also need to check scope below once user self edit actions are added?
    try:
        if is_admin_account:
            bind_context_to_logger(
                {"user_id": str(account_id), "customer_id": str(self_id), "action": action}
            )

            if is_self_edit:
                if action == "set_alias":
                    if details.new_alias is None:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST, detail="Alias must be provided"
                        )

                    # if an empty string, need to convert to None for asyncpg
                    new_alias = details.new_alias if details.new_alias else None

                    update_query = "UPDATE customers SET alias=LOWER($1) WHERE id=$2"
                    query_args = (new_alias, self_id)
                elif action == "set_password":
                    pw = details.passwords.password1.get_secret_value()

                    async with request.state.pgpool.acquire() as con:
                        async with con.transaction():
                            select_query = "SELECT previous_passwords FROM customers WHERE id=$1"
                            update_query = "UPDATE customers SET password=$1, previous_passwords=array_prepend($1, previous_passwords[0:4]) WHERE id=$2"
                            query_params = [account_id]
                            # query for previous passwords
                            row = await con.fetchrow(select_query, *query_params)
                            # returning so last update does not get executed
                            return await _update_password(
                                con, pw, row["previous_passwords"], update_query, query_params
                            )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid admin-edit-self action: {action}",
                    )
            else:
                if action == "deactivate":
                    update_query = "UPDATE users SET suspended='t' WHERE id=$1 AND customer_id=$2"
                    query_args = (account_id, self_id)
                elif action == "reactivate":
                    # when reactivated, failed login attempts should be set back to 0.
                    update_query = "UPDATE users SET suspended='f', failed_login_attempts=0 WHERE id=$1 AND customer_id=$2"
                    query_args = (account_id, self_id)
                elif action == "delete":
                    update_query = "UPDATE users SET deleted_at=$1 WHERE id=$2 AND customer_id=$3"
                    query_args = (datetime.now(), account_id, self_id)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid admin-edit-user action: {action}",
                    )

        elif is_user_account:
            # TODO unit test this else branch
            bind_context_to_logger(
                {"user_id": str(self_id), "customer_id": token.customer_id, "action": action}
            )

            if is_self_edit:
                if action == "set_password":
                    customer_id = uuid.UUID(hex=token.customer_id)
                    pw = details.passwords.password1.get_secret_value()

                    async with request.state.pgpool.acquire() as con:
                        async with con.transaction():
                            select_query = (
                                "SELECT previous_passwords FROM users WHERE id=$1 AND customer_id=$2"
                            )
                            update_query = "UPDATE users SET password=$1, previous_passwords=array_prepend($1, previous_passwords[0:4]) WHERE id=$2 AND customer_id=$3"
                            query_params = [account_id, customer_id]
                            # query for previous passwords
                            row = await con.fetchrow(select_query, *query_params)
                            # returning so last update does not get executed
                            return await _update_password(
                                con, pw, row["previous_passwords"], update_query, query_params
                            )

            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User accounts cannot edit details of other accounts",
                )

        async with request.state.pgpool.acquire() as con:
            await con.execute(update_query, *query_args)

    except UnableToUpdateAccountError:
        msg = "Cannot set password to any of the previous 5 passwords"
        logger.exception(f"PUT /{account_id}: {msg}")
        return UnableToUpdateAccountResponse(message=msg)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"PUT /{account_id}: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
