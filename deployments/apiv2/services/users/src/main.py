import logging
import json
from typing import Union, List, Optional
import uuid
from datetime import datetime
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from asyncpg.exceptions import UniqueViolationError
from fastapi import FastAPI, Request, Depends, HTTPException, status, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from jwt.exceptions import InvalidTokenError
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
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
    UserAction,
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
        CB_CUSTOMER_ID = await con.fetchval("SELECT id FROM customers WHERE email = 'software@curibio.com'")


@app.post("/login", response_model=LoginResponse)
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

    is_customer_login_attempt = type(details) is CustomerLogin

    if is_customer_login_attempt:
        account_type = "customer"
        email = details.email.lower()
        select_query = (
            "SELECT password, id, data->'scope' AS scope "
            "FROM customers WHERE deleted_at IS NULL AND email = $1"
        )
        select_query_params = (email,)
        customer_id = None

        update_last_login_query = (
            "UPDATE customers SET last_login = $1 WHERE deleted_at IS NULL AND email = $2"
        )
        update_last_login_params = (datetime.now(), email)
    else:
        account_type = "user"
        username = details.username.lower()
        # suspended is for deactivated accounts and verified is for new users needing to verify through email
        # select for service specific usage restrictions listed under the customer account
        select_query = "SELECT password, id, data->'scope' AS scope FROM users WHERE deleted_at IS NULL AND name=$1 AND customer_id=$2 AND suspended='f' AND verified='t'"
        select_query_params = (username, str(details.customer_id))
        customer_id = details.customer_id

        update_last_login_query = "UPDATE users SET last_login = $1 WHERE deleted_at IS NULL AND name = $2 AND customer_id=$3 AND suspended='f' AND verified='t'"
        update_last_login_params = (datetime.now(), username, str(details.customer_id))

    client_type = details.client_type if details.client_type else "unknown"
    logger.info(f"{account_type.title()} login attempt from client '{client_type}'")

    failed_msg = "Invalid credentials"
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
                # both users and customers have scopes
                # check account usage quotas
                cust_id = customer_id if customer_id is not None else row["id"]
                usage_quota = await check_customer_quota(con, str(cust_id), details.service)
                scope = json.loads(row.get("scope", "[]"))

                if is_customer_login_attempt:
                    # get tier of service scope in list of customer scopes
                    scope = [s for s in scope if details.service in s]
                    if not scope:
                        raise LoginError("No scope for service found in customer scopes")

                    # replace with customer scope
                    _, customer_tier = split_scope_account_data(scope[0])
                    scope[0] = f"customer:{customer_tier}"

                # if login was successful, then update last_login column to now
                await con.execute(update_last_login_query, *update_last_login_params)

                tokens = await _create_new_tokens(con, row["id"], customer_id, scope, account_type)
                return LoginResponse(tokens=tokens, usage_quota=usage_quota)

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
    token=Depends(ProtectedAny(scope=CUSTOMER_SCOPES)),
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
            insert_query = "INSERT INTO customers (email, password, data, usage_restrictions) VALUES ($1, $2, $3, $4) RETURNING id"
            query_params = (email, phash, json.dumps({"scope": scope}), json.dumps(dict(PULSE3D_PAID_USAGE)))
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

            query_params = (
                username,
                email,
                customer_tier,
                json.dumps({"scope": user_scope}),
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
    except Exception as e:
        logger.exception(f"register: Unexpected error {repr(e)}")
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

    except Exception as e:
        logger.exception(f"GET /email: Unexpected error {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def _create_user_email(
    *,
    con,
    type: str,
    user_id: uuid.UUID,
    customer_id: Optional[uuid.UUID],
    scopes: List[str],
    name: Optional[str],
    email: EmailStr,
):
    try:
        scope = scopes[0]
        if "user" in scope:
            account_type = "user"
            query = "UPDATE users SET pw_reset_verify_link=$1 WHERE id=$2"
        elif "customer" in scope:
            account_type = "customer"
            query = "UPDATE customers SET pw_reset_link=$1 WHERE id=$2"
        else:
            logger.exception(f"Scope {scope} is not allowed to make this request")
            raise Exception()
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
            logger.exception(f"{type} is not a valid type allowed in this request")
            raise Exception()

        # add token to users table after no exception is raised
        # The token  has to be created with id being returned from insert query so it's updated separately
        await con.execute(query, jwt_token.token, user_id)

        # send email with reset token
        await _send_user_email(
            username=name,
            email=email,
            url=url,
            subject=subject,
            template=template,
        )
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
        MAIL_TLS=True,
        MAIL_SSL=False,
        USE_CREDENTIALS=True,
        TEMPLATE_FOLDER="./templates",
    )
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        template_body={
            "username": username if username is not None else "Admin",
            "url": url,
        },  # pass any variables you want to use in the email template
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name=template)


@app.put("/account")
async def update_accounts(
    request: Request,
    details: PasswordModel,
    token=Depends(ProtectedAny(scope=ACCOUNT_SCOPES)),
):
    """Confirm and verify new user and password.

    Used for both resetting new password or verifying new user accounts. Route will check if link has been used or if account has already been verified.
    """
    try:
        user_id = uuid.UUID(hex=token["userid"])
        is_customer = "customer:reset" in token["scope"]
        is_user = "users" in token["scope"][0]
        customer_id = None if is_customer else uuid.UUID(hex=token["customer_id"])

        ph = PasswordHasher()
        phash = ph.hash(details.password1.get_secret_value())

        async with request.state.pgpool.acquire() as con:
            async with con.transaction():
                # ProtectedAny will return 401 already if link has expired
                if is_customer:
                    row = await con.fetchrow(
                        "SELECT pw_reset_link FROM customers WHERE id=$1",
                        user_id,
                    )
                    # link in db gets replaced with NULL when it's been successfully used
                    if row["pw_reset_link"] is None:
                        return UnableToUpdateAccountResponse(message="Link has already been used")

                    await con.execute(
                        "UPDATE customers SET pw_reset_link=NULL, password=$1 WHERE id=$2",
                        phash,
                        user_id,
                    )
                # Luci (12/8/22) don't use catchall else statements with customer versus user conditionals
                elif is_user:
                    row = await con.fetchrow(
                        "SELECT verified, pw_reset_verify_link FROM users WHERE id=$1 AND customer_id=$2",
                        user_id,
                        customer_id,
                    )
                    # if the link is being used to verify account and the account has already been verified, then return message to display to user
                    if details.verify and row["verified"]:
                        return UnableToUpdateAccountResponse(message="Account has already been verified")

                    # link in db gets replaced with NULL when it's been successfully used
                    if row["pw_reset_verify_link"] is None:
                        return UnableToUpdateAccountResponse(message="Link has already been used")

                    # will set verified to True even if it already is to remove extra, unnecessary conditional
                    await con.execute(
                        "UPDATE users SET verified='t', pw_reset_verify_link=NULL, password=$1 WHERE id=$2 AND customer_id=$3",
                        phash,
                        user_id,
                        customer_id,
                    )

    except Exception as e:
        logger.exception(f"PUT /{user_id}: Unexpected error {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/")
async def get_all_users(
    request: Request,
    token=Depends(ProtectedAny(scope=CUSTOMER_SCOPES)),
):
    """Get info for all the users under the given customer account.

    List of users returned will be sorted with all active users showing up first, then all the suspended (deactivated) users
    """
    customer_id = uuid.UUID(hex=token["userid"])

    query = (
        "SELECT id, name, email, created_at, last_login, verified, suspended, pw_reset_verify_link "
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
            if row["pw_reset_verify_link"] is not None:
                try:
                    decode_token(row["pw_reset_verify_link"])
                except jwt.exceptions.ExpiredSignatureError:
                    row["pw_reset_verify_link"] = None

        return formatted_results

    except Exception as e:
        logger.exception(f"GET /: Unexpected error {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Luci (10/5/22) Following two routes need to be last otherwise will mess with the ProtectedAny scope used in Auth
# Please see https://fastapi.tiangolo.com/tutorial/path-params/#order-matters
@app.get("/{user_id}")
async def get_user(
    request: Request,
    user_id: uuid.UUID,
    token=Depends(ProtectedAny(scope=CUSTOMER_SCOPES)),
):
    """Get info for the user with the given under the given customer account."""
    customer_id = uuid.UUID(hex=token["userid"])

    query = (
        "SELECT id, name, email, created_at, last_login, suspended FROM users "
        "WHERE customer_id=$1 AND id=$2 AND deleted_at IS NULL"
    )
    try:
        async with request.state.pgpool.acquire() as con:
            row = await con.fetchrow(query, customer_id, user_id)

        if not row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User ID: {user_id} not found under Customer ID: {customer_id}",
            )

        return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"GET /{user_id}: Unexpected error {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.put("/{user_id}")
async def update_user(
    request: Request,
    details: UserAction,
    user_id: uuid.UUID,
    token=Depends(ProtectedAny(scope=CUSTOMER_SCOPES)),
):
    """Update a user's information in the database.

    The action to take on the user should be passed in the body of PUT request as action_type:
        - deactivate: set suspended field to true
        - delete: set deleted_at field to current time
    """
    action = details.action_type

    if action in ("deactivate", "reactivate"):
        suspended = action == "deactivate"
        update_query = "UPDATE users SET suspended=$1 WHERE id=$2"
        query_args = (
            suspended,
            user_id,
        )
    elif action == "delete":
        update_query = "UPDATE users SET deleted_at=$1 WHERE id=$2"
        query_args = (datetime.now(), user_id)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action type")

    try:
        async with request.state.pgpool.acquire() as con:
            await con.execute(update_query, *query_args)
    except Exception as e:
        logger.exception(f"PUT /{user_id}: Unexpected error {repr(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
