import json
import time
import uuid
from datetime import datetime

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from asyncpg.exceptions import UniqueViolationError
from fastapi import FastAPI, Request, Depends, HTTPException, status, Response, Query
from fastapi.middleware.cors import CORSMiddleware
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
    check_prohibited_user_scopes,
    check_prohibited_admin_scopes,
    convert_scope_str,
    ScopeTags,
    Scopes,
    PULSE3D_PAID_USAGE,
    ProhibitedScopeError,
    AuthTokens,
    get_account_scopes,
    create_new_tokens,
    AccountTypes,
)
from jobs import check_customer_quota
from core.config import DATABASE_URL, CURIBIO_EMAIL, CURIBIO_EMAIL_PASSWORD, DASHBOARD_URL
from models.errors import LoginError, RegistrationError, EmailRegistrationError
from models.users import (
    AdminLogin,
    UserLogin,
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

app = FastAPI(openapi_url=None)

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


@app.on_event("startup")
async def startup():
    await asyncpg_pool()


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
                "FROM customers WHERE deleted_at IS NULL AND email=$1",
                email,
            )

            # query will return None if customer email is not found
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
            # get scopes from account_scopes table
            scopes = await get_account_scopes(con, customer_id, True)

            # TODO split this part out into a new route
            # get list of scopes that the admin can assign to its users
            avail_user_scopes = get_assignable_user_scopes(scopes)
            user_scope_dependencies = get_scope_dependencies(avail_user_scopes)
            avail_admin_scopes = get_assignable_admin_scopes(scopes)
            admin_scope_dependencies = get_scope_dependencies(avail_admin_scopes)

            # TODO decide how to show admin accounts usage data for multiple products, defaulting to mantarray now
            # check usage for customer
            usage_quota = await check_customer_quota(con, str(customer_id), "mantarray")

            # if login was successful, then update last_login column value to now
            await con.execute(
                "UPDATE customers SET last_login=$1, failed_login_attempts=0 WHERE deleted_at IS NULL AND email=$2",
                datetime.now(),
                email,
            )

            tokens = await create_new_tokens(con, None, customer_id, scopes, account_type)

            # TODO fix tests for this?
            return LoginResponse(
                tokens=tokens,
                usage_quota=usage_quota,
                user_scopes=user_scope_dependencies,
                admin_scopes=admin_scope_dependencies,
            )

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
            "SELECT password, id, failed_login_attempts, suspended, customer_id FROM users "
            "WHERE deleted_at IS NULL AND name=$1 AND customer_id=$2 AND verified='t'"
        )
    else:
        # if no UUID given, the check against the customer account alias
        # TODO should make sure an alias is actually set here?
        select_query = (
            "SELECT u.password, u.id, u.failed_login_attempts, u.suspended, u.customer_id "
            "FROM users AS u JOIN customers AS c ON u.customer_id=c.id "
            "WHERE u.deleted_at IS NULL AND u.name=$1 AND LOWER(c.alias)=LOWER($2) AND u.verified='t'"
        )

    client_type = details.client_type if details.client_type else "unknown"

    bind_context_to_logger(
        {"customer_id": str(customer_id), "username": username, "client_type": client_type}
    )

    logger.info(f"User login attempt from client '{client_type}'")

    try:
        async with request.state.pgpool.acquire() as con:
            select_query_result = await con.fetchrow(select_query, username, str(details.customer_id))

            # query will return None if username is not found
            if select_query_result is not None:
                user_id = select_query_result.get("id")
                customer_id = select_query_result.get("customer_id")
                # rebind customer id with uuid incase an alias was used above
                bind_context_to_logger({"customer_id": str(customer_id), "user_id": str(user_id)})

            pw = details.password.get_secret_value()

            # verify password, else raise LoginError
            await _verify_password(con, account_type, pw, select_query_result)

            #  get scopes from account_scopes table
            scopes = await get_account_scopes(con, user_id, False)

            # users logging into the dashboard should not have usage returned because they need to select a product from the landing page first to be given correct limits
            # users logging into a specific instrument need the the usage returned right away and it is known what instrument they are using
            usage_quota = None
            if (service := details.service) is not None:
                # TODO Luci (09/30/23): remove after all users upgrade to MA controller v1.2.2+, handling for pulse3d login types will no longer be needed
                service = service if service != "pulse3d" else "mantarray"
                usage_quota = await check_customer_quota(con, str(customer_id), service)

            # if login was successful, then update last_login column value to now
            # Tanner (7/25/23): using the customer ID returned from the select query since the customer ID field passed in with the request may contain an alias
            await con.execute(
                "UPDATE users SET last_login=$1, failed_login_attempts=0 "
                "WHERE deleted_at IS NULL AND name=$2 AND customer_id=$3 AND verified='t'",
                datetime.now(),
                username,
                str(customer_id),
            )

            tokens = await create_new_tokens(con, user_id, customer_id, scopes, account_type)

            return LoginResponse(tokens=tokens, usage_quota=usage_quota)

    except LoginError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception:
        logger.exception("POST /login: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def _verify_password(con, account_type, pw, select_query_result) -> None:
    ph = PasswordHasher()

    failed_msg = "Invalid credentials. Account will be locked after 10 failed attempts."
    account_locked_msg = "Account locked. Too many failed attempts."

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
        logger.info(
            f"Failed login attempt {select_query_result['failed_login_attempts'] + 1} for {account_type} id: {select_query_result['id']}"
        )
        updated_failed_attempts = select_query_result["failed_login_attempts"] + 1
        await _update_failed_login_attempts(
            con, account_type, select_query_result["id"], updated_failed_attempts
        )
        # update login error if this failed attempt hits limit
        raise LoginError(
            account_locked_msg if updated_failed_attempts == MAX_FAILED_LOGIN_ATTEMPTS else failed_msg
        )
    except InvalidHash:
        """
        The user or admin wasn't found but we don't want to leak info about valid users/admins
        through timing analysis so we still hash the supplied password before returning an error
        """
        ph.hash(pw)
        raise LoginError(failed_msg)
    else:
        # only raise LoginError here when account is locked on successful creds after they have been checked to prevent giving away facts about successful login combinations
        if select_query_result["failed_login_attempts"] >= MAX_FAILED_LOGIN_ATTEMPTS:
            raise LoginError(account_locked_msg)
        # user can be suspended if admin account suspends them, select_query_result will not return None in that instance
        if select_query_result["suspended"]:
            raise LoginError(failed_msg)


async def _update_failed_login_attempts(con, account_type: str, id: str, count: int) -> None:
    if count == MAX_FAILED_LOGIN_ATTEMPTS:
        # if max failed attempts is reached, then deactivate the account and increment count
        update_query = f"UPDATE {account_type}s SET suspended='t', failed_login_attempts=failed_login_attempts+1 where id=$1"
    else:
        # else increment failed attempts
        update_query = f"UPDATE {account_type}s SET failed_login_attempts=failed_login_attempts+1 where id=$1"

    await con.execute(update_query, id)


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

            scopes = await get_account_scopes(con, account_id, is_admin_account)

            # con is passed to this function, so it must be inside this async with block
            user_id = None if is_admin_account else account_id
            customer_id = account_id if is_admin_account else row["customer_id"]
            return await create_new_tokens(con, user_id, customer_id, scopes, account_type)

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

        check_prohibited_admin_scopes(details.scopes, token.scopes)

        async with request.state.pgpool.acquire() as con:
            async with con.transaction():
                try:
                    insert_account_query_args = (
                        "INSERT INTO customers (email, usage_restrictions) VALUES ($1, $2) RETURNING id",
                        email,
                        json.dumps(dict(PULSE3D_PAID_USAGE)),
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
                await _create_account_email(
                    con=con,
                    type="verify",
                    user_id=None,
                    customer_id=new_account_id,
                    scope=Scopes.ADMIN__VERIFY,
                    name=None,
                    email=email,
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

        logger.info(f"Registering new user with scopes: {user_scopes}")

        # suspended and verified get set to False by default
        insert_account_query_args = (
            "INSERT INTO users (name, email, customer_id) VALUES ($1, $2, $3) RETURNING id",
            username,
            email,
            customer_id,
        )

        async with request.state.pgpool.acquire() as con:
            async with con.transaction():
                try:
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
                await _create_account_email(
                    con=con,
                    type="verify",
                    user_id=new_account_id,
                    customer_id=customer_id,
                    scope=Scopes.USER__VERIFY,
                    name=username,
                    email=email,
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
    request: Request, email: EmailStr = Query(None), type: str = Query(None), user: bool = Query(None)
):
    """Send or resend account emails.

    No token required for request. Currently sending reset password and new registration emails based on query type.
    """
    # EmailRegistrationError will be raised if random type param is added that isn't verify or reset
    try:
        async with request.state.pgpool.acquire() as con:
            query = (
                "SELECT id, customer_id, name FROM users WHERE email=$1"
                if user
                else "SELECT id FROM customers WHERE email=$1"
            )

            row = await con.fetchrow(query, email)

            # send email if found, otherwise return 204, doesn't need to raise an exception
            if row is None:
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
            scope = convert_scope_str(f"{'user' if user else 'admin'}:{type}")

            await _create_account_email(
                con=con,
                type=type,
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
    type: str,
    user_id: uuid.UUID | None,
    customer_id: uuid.UUID,
    scope: Scopes,
    name: str | None,
    email: EmailStr,
):
    try:
        if ScopeTags.ACCOUNT not in scope.tags:
            raise Exception(f"Scope {scope} is not allowed in an email token")

        account_type = AccountTypes.USER if "user" in scope else AccountTypes.ADMIN

        query = f"UPDATE {account_type}s SET reset_token=$1 WHERE id=$2"

        # create email verification token, exp 24 hours
        jwt_token = create_token(
            userid=user_id, customer_id=customer_id, scopes=[scope], account_type=account_type
        )

        url = f"{DASHBOARD_URL}/account/{type}?token={jwt_token.token}"

        # assign correct email template and redirect url based on request type
        if type == "reset":
            subject = "Reset your password"
            template = "reset_password.html"
        elif type == "verify":
            subject = "Please verify your email address"
            template = "registration.html"
        else:
            logger.error(f"{type} is not a valid type allowed in this request")
            raise Exception()

        # add token to users table after no exception is raised
        # The token  has to be created with id being returned from insert query so it's updated separately
        await con.execute(query, jwt_token.token, user_id)

        # send email with reset token
        await _send_account_email(username=name, email=email, url=url, subject=subject, template=template)
    except Exception as e:
        raise EmailRegistrationError(e)


async def _send_account_email(
    *, username: str, email: EmailStr, url: str, subject: str, template: str
) -> None:
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
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        subtype=MessageType.html,
        template_body={
            "username": username if username is not None else "Admin",
            "url": url,
        },  # pass any variables you want to use in the email template
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
        ph = PasswordHasher()
        phash = ph.hash(pw)

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
                    return UnableToUpdateAccountResponse(message="Account has already been verified")
                # token in db gets replaced with NULL when it's been successfully used
                if row["reset_token"] is None:
                    return UnableToUpdateAccountResponse(message="Link has already been used")

                # if there is a token present in the DB but it does not match the one provided to this route, then presumably a new one has been created and thus the one being used should be considered expired
                try:
                    # decode and validate current reset token
                    current_token = decode_token(row["reset_token"])
                    # make sure the given token and the current token in the DB are the same
                    assert token == current_token
                except (InvalidTokenError, AssertionError):
                    return UnableToUpdateAccountResponse(message="Link has expired")

                # make sure new password does not match any previous passwords on file
                for prev_pw in row["previous_passwords"]:
                    try:
                        ph.verify(prev_pw, pw)
                    except VerifyMismatchError:
                        # passwords don't match, nothing else to do
                        continue
                    else:
                        # passwords match, return msg indicating that this is the case
                        return UnableToUpdateAccountResponse(
                            message="Cannot set password to any of the previous 5 passwords"
                        )

                # Update the password of the account, and if it is a user also set the account as verified
                query = (
                    "UPDATE customers SET reset_token=NULL, password=$1, previous_passwords=array_prepend($1, previous_passwords[0:4]) WHERE id=$2"
                    if is_admin
                    else "UPDATE users SET verified='t', reset_token=NULL, password=$1, previous_passwords=array_prepend($1, previous_passwords[0:4]) WHERE id=$2 AND customer_id=$3"
                )
                query_params = [phash, account_id]

                if is_user:
                    query_params.append(customer_id)

                await con.execute(query, *query_params)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"PUT /{account_id}: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/")
async def get_all_users(request: Request, token=Depends(ProtectedAny(tag=ScopeTags.ADMIN))):
    """Get info for all the users under the given admin account.

    List of users returned will be sorted with all active users showing up first, then all the suspended (deactivated) users
    """
    customer_id = uuid.UUID(hex=token.customer_id)

    bind_context_to_logger({"customer_id": str(customer_id), "user_id": None})

    query = (
        "SELECT u.id, u.name, u.email, u.created_at, u.last_login, u.verified, u.suspended, u.reset_token, array_agg(s.scope) as scopes "
        "FROM users u "
        "INNER JOIN account_scopes s ON u.id=s.user_id "
        "WHERE u.customer_id=$1 AND u.deleted_at IS NULL "
        "GROUP BY u.id, u.name, u.email, u.created_at, u.last_login, u.verified, u.suspended, u.reset_token "
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
    user_scopes = details.scopes

    bind_context_to_logger({"customer_id": str(customer_id), "user_id": str(account_id)})

    try:
        check_prohibited_user_scopes(user_scopes, admin_scopes)

        async with request.state.pgpool.acquire() as con:
            async with con.transaction():
                # first delete existing scopes from database
                await con.execute(
                    "DELETE FROM account_scopes WHERE customer_id=$1 AND user_id=$2", customer_id, account_id
                )
                # add new scopes
                await con.execute(
                    "INSERT INTO account_scopes VALUES ($1, $2, unnest($3::text[]))",
                    customer_id,
                    account_id,
                    user_scopes,
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


@app.put("/{account_id}")
async def update_user(
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
        - a user account updating itself (not yet available)

    The action to take on the user should be passed in the body of PUT request as action_type:
        - deactivate (admin->user): set suspended field to true
        - delete (admin->user): set deleted_at field to current time
        - set_alias (admin->self): set the alias field to the given value
    """
    self_id = uuid.UUID(hex=token.account_id)
    action = details.action_type

    is_admin_account = token.account_type == AccountTypes.ADMIN
    is_self_edit = self_id == account_id

    # TODO also need to check scope below once user self edit actions are added?

    if is_admin_account:
        bind_context_to_logger({"user_id": str(account_id), "customer_id": str(self_id), "action": action})

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
                update_query = (
                    "UPDATE users SET suspended='f', failed_login_attempts=0 WHERE id=$1 AND customer_id=$2"
                )
                query_args = (account_id, self_id)
            elif action == "delete":
                update_query = "UPDATE users SET deleted_at=$1 WHERE id=$2 AND customer_id=$3"
                query_args = (datetime.now(), account_id, self_id)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid admin-edit-user action: {action}",
                )
    else:
        # TODO unit test this else branch
        bind_context_to_logger({"user_id": str(self_id), "customer_id": token.customer_id, "action": action})

        if not is_self_edit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User accounts cannot edit details of other accounts",
            )

        # Tanner (7/25/23): there are currently no actions a user account can take on itself
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid user-edit-self action: {action}"
        )

    try:
        async with request.state.pgpool.acquire() as con:
            await con.execute(update_query, *query_args)
    except Exception:
        logger.exception(f"PUT /{account_id}: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
