import logging
import json
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
from auth import (
    ProtectedAny,
    create_token,
    decode_token,
    CUSTOMER_SCOPES,
    split_scope_account_data,
    ACCOUNT_SCOPES,
    PULSE3D_PAID_USAGE,
)
from jobs import check_customer_quota
from core.config import DATABASE_URL, CURIBIO_EMAIL, CURIBIO_EMAIL_PASSWORD, DASHBOARD_URL
from models.errors import LoginError, RegistrationError, EmailRegistrationError
from models.tokens import AuthTokens
from models.users import (
    CustomerLogin,
    UserLogin,
    CustomerCreate,
    UserCreate,
    CustomerProfile,
    UserProfile,
    AccountUpdateAction,
    LoginResponse,
    PasswordModel,
    UnableToUpdateAccountResponse,
)
from utils.db import AsyncpgPoolDep
from fastapi.templating import Jinja2Templates

# logging is configured in log_config.yaml
logger = logging.getLogger(__name__)

asyncpg_pool = AsyncpgPoolDep(dsn=DATABASE_URL)

app = FastAPI(openapi_url=None)

CB_CUSTOMER_ID: uuid.UUID
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
        CB_CUSTOMER_ID = await con.fetchval("SELECT id FROM customers WHERE email='software@curibio.com'")


@app.post("/login", response_model=LoginResponse)
async def login(request: Request, details: UserLogin | CustomerLogin):
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

    # Tanner (7/24/23): checking the type instead of using isinstance here in case UserLogin and CustomerLogin are ever put into the class hierarchy which would cause the isinstance approach to fail in some cases
    is_customer_login_attempt = type(details) is CustomerLogin

    if is_customer_login_attempt:
        account_type = "customer"
        email = details.email.lower()
        select_query = (
            "SELECT password, id, failed_login_attempts, suspended "
            "FROM customers WHERE deleted_at IS NULL AND email=$1"
        )
        select_query_params = (email,)

        update_last_login_query = "UPDATE customers SET last_login=$1, failed_login_attempts=0 WHERE deleted_at IS NULL AND email=$2"
        update_last_login_params = (datetime.now(), email)
    else:
        account_type = "user"
        username = details.username.lower()
        # select for service specific usage restrictions listed under the customer account
        # suspended is for deactivated accounts and verified is for new users needing to verify through email
        # Tanner (7/25/23): need to use separate queries since asyncpg will raise an error if the value passed in to be compared against customer_id is not a UUID
        if isinstance(details.customer_id, uuid.UUID):
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
                "WHERE u.deleted_at IS NULL AND u.name=$1 AND c.alias=$2 AND u.verified='t'"
            )
        select_query_params = (username, str(details.customer_id))

        update_last_login_query = (
            "UPDATE users SET last_login=$1, failed_login_attempts=0 "
            "WHERE deleted_at IS NULL AND name=$2 AND customer_id=$3 AND verified='t'"
        )
        # the value for customer ID will be added later
        update_last_login_params = (datetime.now(), username)

    client_type = details.client_type if details.client_type else "unknown"
    logger.info(f"{account_type.title()} login attempt from client '{client_type}'")

    failed_msg = "Invalid credentials"
    account_locked_msg = "Account locked after too many failed login attempts"

    try:
        async with request.state.pgpool.acquire() as con:
            select_query_result = await con.fetchrow(select_query, *select_query_params)
            pw = details.password.get_secret_value()

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

                # increment customer/user failed attempts
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
                The user or customer wasn't found but we don't want to leak info about valid users/customers
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

                # check account usage quotas
                customer_id = select_query_result["id" if is_customer_login_attempt else "customer_id"]
                usage_quota = await check_customer_quota(con, str(customer_id), details.service)

                scope = await _get_account_scope(con, select_query_result["id"], is_customer_login_attempt)

                if is_customer_login_attempt:
                    scope = _convert_to_customer_scope(scope, details.service)
                    # customer account tokens don't require a customer ID
                    customer_id = None
                else:
                    # Tanner (7/25/23): using the customer ID returned from the select query since the customer ID
                    # field passed in with the request may contain an alias
                    update_last_login_params = (*update_last_login_params, str(customer_id))

                # if login was successful, then update last_login column value to now
                await con.execute(update_last_login_query, *update_last_login_params)

                tokens = await _create_new_tokens(
                    con, select_query_result["id"], customer_id, scope, account_type
                )
                return LoginResponse(tokens=tokens, usage_quota=usage_quota)

    except LoginError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception:
        logger.exception("POST /login: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def _update_failed_login_attempts(con, account_type: str, id: str, count: int) -> None:
    if count == MAX_FAILED_LOGIN_ATTEMPTS:
        # if max failed attempts is reached, then deactivate the account and increment count
        update_query = f"UPDATE {account_type}s SET suspended='t', failed_login_attempts=failed_login_attempts+1 where id=$1"
    else:
        # else increment failed attempts
        update_query = f"UPDATE {account_type}s SET failed_login_attempts=failed_login_attempts+1 where id=$1"

    await con.execute(update_query, id)


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

    is_customer_account = account_type == "customer"

    if is_customer_account:
        select_query = "SELECT refresh_token FROM customers WHERE id=$1"
    else:
        select_query = "SELECT refresh_token, customer_id FROM users WHERE id=$1"

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

            scope = await _get_account_scope(con, userid, is_customer_account)

            if is_customer_account:
                service_scope = next(s for s in token["scope"] if s.startswith("service:"))
                service_name = service_scope.split(":")[-1]
                scope = _convert_to_customer_scope(scope, service_name)

            # con is passed to this function, so it must be inside this async with block
            return await _create_new_tokens(con, userid, row.get("customer_id"), scope, account_type)

    except HTTPException:
        raise
    except Exception:
        logger.exception("POST /refresh: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def _get_account_scope(db_con, account_id, is_customer_account):
    if is_customer_account:
        query = "SELECT scope FROM account_scopes WHERE customer_id=$1 AND user_id IS NULL"
    else:
        query = "SELECT scope FROM account_scopes WHERE user_id=$1"

    query_res = await db_con.fetch(query, account_id)
    scope = [row["scope"] for row in query_res]
    return scope


def _convert_to_customer_scope(scope, service):
    # get tier of service scope in list of customer scopes
    scope_for_service = [s for s in scope if service in s]
    if not scope_for_service:
        raise LoginError(f"No scope for service '{service}' found in customer scopes: {scope}")

    # replace with customer scope
    _, customer_tier = split_scope_account_data(scope_for_service[0])
    return [f"customer:{customer_tier}", f"service:{service}"]


async def _create_new_tokens(db_con, userid, customer_id, scope, account_type):
    refresh_scope = ["refresh"]
    try:
        service_scope_for_refresh = next(s for s in scope if s.startswith("service:"))
    except StopIteration:
        pass
    else:
        scope.remove(service_scope_for_refresh)
        refresh_scope.append(service_scope_for_refresh)

    # create new tokens
    access = create_token(
        userid=userid, customer_id=customer_id, scope=scope, account_type=account_type, refresh=False
    )
    # refresh token does not need any scope, so just set it to refresh
    refresh = create_token(
        userid=userid, customer_id=customer_id, scope=refresh_scope, account_type=account_type, refresh=True
    )

    # insert refresh token into DB
    if account_type == "customer":
        update_query = "UPDATE customers SET refresh_token=$1 WHERE id=$2"
    else:
        update_query = "UPDATE users SET refresh_token=$1 WHERE id=$2"

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
        update_query = "UPDATE customers SET refresh_token = NULL WHERE id=$1"
    else:
        update_query = "UPDATE users SET refresh_token = NULL WHERE id=$1"

    try:
        async with request.state.pgpool.acquire() as con:
            await con.execute(update_query, userid)

    except Exception:
        logger.exception("POST /logout: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/register", response_model=UserProfile | CustomerProfile, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request, details: CustomerCreate | UserCreate, token=Depends(ProtectedAny(scope=CUSTOMER_SCOPES))
):
    """Register a user or customer account.

    Only customer accounts with admin privileges can register users, and only the Curi Bio customer account
    can create new customers.

    If the customer ID in the auth token matches the Curi Bio Customer ID *AND* no username is given,
    assume this is an attempt to register a new customer account.

    Otherwise, attempt to register a regular user under the customer ID in the auth token
    """
    customer_id = uuid.UUID(hex=token["userid"])
    # 'customer:paid' or 'customer:free'
    customer_scope = token["scope"]
    try:
        is_customer_registration_attempt = (
            customer_id == CB_CUSTOMER_ID and type(details) is CustomerCreate  # noqa: F821
        )

        register_type = "customer" if is_customer_registration_attempt else "user"
        logger.info(f"Attempting {register_type} registration")
        email = details.email.lower()
        # scope will not be sent in request body for both customer and user registration
        if is_customer_registration_attempt:
            ph = PasswordHasher()
            phash = ph.hash(details.password1.get_secret_value())
            scope = details.scope
            insert_query = "INSERT INTO customers (email, password, previous_passwords, data, usage_restrictions) VALUES ($1, $2, ARRAY[$3], $4, $5) RETURNING id"
            query_params = (
                email,
                phash,
                phash,
                json.dumps({"scope": scope}),
                json.dumps(dict(PULSE3D_PAID_USAGE)),
            )
        else:
            # TODO add handling for multiple service scopes and exception handling if none found
            _, customer_tier = split_scope_account_data(customer_scope[0])  # 'free' or 'paid'
            # eventually scopes will be passed from FE, but for now just auto set to paid user
            user_scope = details.scope if details.scope is not None else ["pulse3d:paid"]
            username = details.username.lower()
            # suspended and verified get set to False by default
            insert_query = (
                "INSERT INTO users (name, email, account_type, data, customer_id) "
                "VALUES ($1, $2, $3, $4, $5) RETURNING id"
            )

            query_params = (username, email, customer_tier, json.dumps({"scope": user_scope}), customer_id)

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
                        failed_msg = "Email already in use"
                    else:
                        # default catch-all error message
                        failed_msg = "Account registration failed"
                    raise RegistrationError(failed_msg)

                # only send verification emails to new users, not new customers and if successful
                if not is_customer_registration_attempt:
                    await _create_user_email(
                        con=con,
                        type="verify",
                        user_id=result,
                        customer_id=customer_id,
                        scopes=["users:verify"],
                        name=username,
                        email=email,
                    )
                if is_customer_registration_attempt:
                    return CustomerProfile(email=email, user_id=result.hex, scope=details.scope)
                else:
                    return UserProfile(
                        username=username,
                        email=email,
                        user_id=result.hex,
                        account_type=customer_tier,
                        scope=user_scope,
                    )

    except EmailRegistrationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RegistrationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception("POST /register: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/email", status_code=status.HTTP_204_NO_CONTENT)
async def email_user(
    request: Request, email: EmailStr = Query(None), type: str = Query(None), user: bool = Query(None)
):
    """Send or resend user account emails.

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
            if row is not None:
                await _create_user_email(
                    con=con,
                    type=type,
                    user_id=row["id"],
                    customer_id=row.get("customer_id", None),
                    scopes=[f"{'users' if user else 'customer'}:{type}"],
                    name=row.get("name", None),
                    email=email,
                )

    except Exception:
        logger.exception("GET /email: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def _create_user_email(
    *,
    con,
    type: str,
    user_id: uuid.UUID,
    customer_id: uuid.UUID | None,
    scopes: list[str],
    name: str | None,
    email: EmailStr,
):
    try:
        scope = scopes[0]
        if "user" in scope:
            account_type = "user"
        elif "customer" in scope:
            account_type = "customer"
        else:
            raise Exception(f"Scope {scope} is not allowed to make this request")

        query = f"UPDATE {account_type}s SET reset_token=$1 WHERE id=$2"

        # create email verification token, exp 24 hours
        jwt_token = create_token(
            userid=user_id, customer_id=customer_id, scope=scopes, account_type=account_type
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
        await _send_user_email(username=name, email=email, url=url, subject=subject, template=template)
    except Exception as e:
        raise EmailRegistrationError(e)


async def _send_user_email(*, username: str, email: EmailStr, url: str, subject: str, template: str) -> None:
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
    request: Request, details: PasswordModel, token=Depends(ProtectedAny(scope=ACCOUNT_SCOPES))
):
    """Confirm and verify new user and password.

    Used for both resetting new password or verifying new user accounts. Route will check if the token has been used or if account has already been verified.
    """
    try:
        user_id = uuid.UUID(hex=token["userid"])

        is_customer = "customer:reset" in token["scope"]
        is_user = any("users" in scope for scope in token["scope"])
        # must be either a customer or user. Cannot be both or neither
        if not (is_customer ^ is_user):
            logger.error(f"PUT /{user_id}: Invalid scope(s): {token['scope']}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        customer_id = None if is_customer else uuid.UUID(hex=token["customer_id"])

        pw = details.password1.get_secret_value()
        ph = PasswordHasher()
        phash = ph.hash(pw)

        async with request.state.pgpool.acquire() as con:
            async with con.transaction():
                # ProtectedAny will return 401 already if token has expired, so no need to check again

                # get necessary info from DB before making any changes or validating any data
                query = (
                    "SELECT reset_token, previous_passwords FROM customers WHERE id=$1"
                    if is_customer
                    else "SELECT verified, reset_token, previous_passwords FROM users WHERE id=$1 AND customer_id=$2"
                )
                query_params = [user_id]
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
                    if is_customer
                    else "UPDATE users SET verified='t', reset_token=NULL, password=$1, previous_passwords=array_prepend($1, previous_passwords[0:4]) WHERE id=$2 AND customer_id=$3"
                )
                query_params = [phash, user_id]
                if is_user:
                    query_params.append(customer_id)
                await con.execute(query, *query_params)

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"PUT /{user_id}: Unexpected error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/")
async def get_all_users(request: Request, token=Depends(ProtectedAny(scope=CUSTOMER_SCOPES))):
    """Get info for all the users under the given customer account.

    List of users returned will be sorted with all active users showing up first, then all the suspended (deactivated) users
    """
    customer_id = uuid.UUID(hex=token["userid"])

    query = (
        "SELECT id, name, email, created_at, last_login, verified, suspended, reset_token "
        "FROM users "
        "WHERE customer_id=$1 AND deleted_at IS NULL "
        "ORDER BY suspended"
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


# Luci (10/5/22) Following two routes need to be last otherwise will mess with the ProtectedAny scope used in Auth
# Please see https://fastapi.tiangolo.com/tutorial/path-params/#order-matters
@app.get("/{account_id}")
async def get_user(request: Request, account_id: uuid.UUID, token=Depends(ProtectedAny(check_scope=False))):
    """Get info for the account with the given ID.

    If the account is a user account, the ID must exist under the customer ID in the token
    """
    self_id = uuid.UUID(hex=token["userid"])
    is_customer_account = token["account_type"] == "customer"
    is_self_retrieval = self_id == account_id

    get_user_info_query = (
        "SELECT id, name, email, created_at, last_login, suspended FROM users "
        "WHERE customer_id=$1 AND id=$2 AND deleted_at IS NULL"
    )

    if is_customer_account:
        if is_self_retrieval:
            query = "SELECT id, created_at, alias FROM customers WHERE id=$1"
            query_args = (self_id,)
        else:
            # assume that account ID is a user ID since no customer account can retrieve details of another
            query = get_user_info_query
            query_args = (self_id, account_id)

        # this is only being set in case an error is raised later
        customer_id = self_id
    else:
        if not is_self_retrieval:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User accounts cannot retrieve details of other accounts",
            )

        customer_id = uuid.UUID(hex=token["customer_id"])

        query = get_user_info_query
        query_args = (customer_id, account_id)

    try:
        async with request.state.pgpool.acquire() as con:
            row = await con.fetchrow(query, *query_args)

        if not row:
            if is_customer_account and self_id == account_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error retrieving customer account details",
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
    token=Depends(ProtectedAny(check_scope=False)),
):
    """Update an account's information in the database.

    There are three classes of actions that can be taken:
        - a customer account updating one of its user accounts
        - a customer account updating itself
        - a user account updating itself (not yet available)

    The action to take on the user should be passed in the body of PUT request as action_type:
        - deactivate (customer->user): set suspended field to true
        - delete (customer->user): set deleted_at field to current time
        - set_alias (customer->self): set the alias field to the given value
    """
    self_id = uuid.UUID(hex=token["userid"])
    action = details.action_type

    is_customer_account = token["account_type"] == "customer"
    is_self_edit = self_id == account_id

    # TODO also need to check scope below once user self edit actions are added?

    if is_customer_account:
        if is_self_edit:
            if action == "set_alias":
                if details.new_alias is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail="Alias must be provided"
                    )

                # if an empty string, need to convert to None for asyncpg
                new_alias = details.new_alias if details.new_alias else None

                update_query = "UPDATE customers SET alias=$1 WHERE id=$2"
                query_args = (new_alias, self_id)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid customer-edit-self action: {action}",
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
                    detail=f"Invalid customer-edit-user action: {action}",
                )
    else:
        # TODO unit test this else branch
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
