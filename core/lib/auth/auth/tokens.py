from calendar import timegm
from datetime import datetime, timezone, timedelta
from uuid import UUID
import logging


from pydantic import BaseModel
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from .models import JWTMeta, JWTDetails, JWTPayload, Token
from .settings import (
    JWT_SECRET_KEY,
    JWT_AUDIENCE,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_MINUTES,
    EMAIL_VER_TOKEN_EXPIRE_MINUTES,
)
from .scopes import ScopeTags, Scopes

security = HTTPBearer()

logger = logging.getLogger(__name__)


class AuthTokens(BaseModel):
    access: Token
    refresh: Token


class ProtectedAny:
    def __init__(self, *, scopes: list[Scopes] | None = None, tag: ScopeTags | None = None):
        if scopes:
            self.scopes = frozenset(scopes)
        elif tag:
            self.scopes = frozenset(s for s in Scopes if tag in s.tags)
        else:
            raise ValueError("Either a list of scopes or a scope tag must be provided")

    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        token = credentials.credentials

        try:
            payload = decode_token(token)
            payload_scopes = set(payload["scopes"])

            # if checking scope, make sure that the access token has the required scope
            if not self.scopes & payload_scopes:
                raise Exception()

            return payload

        except Exception as e:
            logger.exception(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authenticated user",
                headers={"WWW-Authenticate": "Bearer"},
            )


def decode_token(token: str):
    return jwt.decode(token, key=str(JWT_SECRET_KEY), algorithms=JWT_ALGORITHM, audience=JWT_AUDIENCE)


def create_token(
    *, userid: UUID, customer_id: UUID | None, scopes: list[Scopes], account_type: str, refresh: bool = False
):
    # make sure tokens have at least 1 scope
    if not scopes:
        raise ValueError("Tokens must have at least 1 scope")
    # make sure account type is valid
    if account_type not in ("user", "customer"):
        raise ValueError(f"Valid account types are 'user' and 'customer', not '{account_type}'")
    if account_type == "user":
        # make sure a user is not given admin privileges
        if any("customer" in s for s in scopes):
            raise ValueError(f"User tokens cannot have scope '{scopes}'")
        if not customer_id:
            raise ValueError("User tokens must have a customer ID")
        customer_id = customer_id.hex
    if account_type == "customer":
        if customer_id:
            raise ValueError("Customer tokens cannot have a customer ID")

    if refresh:
        if non_refresh_scopes := list(set(scopes) - {Scopes.REFRESH}):
            raise ValueError(f"Invalid scopes for refresh token {non_refresh_scopes}")
    elif Scopes.REFRESH in scopes:
        raise ValueError("access token cannot contain 'refresh' scope")

    # three different constant exp times based on token type
    if refresh:
        exp_dur = REFRESH_TOKEN_EXPIRE_MINUTES  # 30min
    elif any(s for s in scopes if ScopeTags.ACCOUNT in s.tags):
        exp_dur = EMAIL_VER_TOKEN_EXPIRE_MINUTES  # 24hr
    else:
        exp_dur = ACCESS_TOKEN_EXPIRE_MINUTES  # 5min

    now = datetime.now(tz=timezone.utc)
    iat = timegm(now.utctimetuple())
    exp = timegm((now + timedelta(minutes=exp_dur)).utctimetuple())
    jwt_meta = JWTMeta(aud=JWT_AUDIENCE, scopes=scopes, iat=iat, exp=exp, refresh=refresh)
    jwt_details = JWTDetails(customer_id=customer_id, userid=userid.hex, account_type=account_type)
    jwt_payload = JWTPayload(**jwt_meta.dict(), **jwt_details.dict())

    jwt_token = jwt.encode(payload=jwt_payload.dict(), key=str(JWT_SECRET_KEY), algorithm=JWT_ALGORITHM)

    return Token(token=jwt_token)


# TODO add testing for all this
async def get_account_scope(db_con, account_id, is_customer_account):
    if is_customer_account:
        query = "SELECT scope FROM account_scopes WHERE customer_id=$1 AND user_id IS NULL"
    else:
        query = "SELECT scope FROM account_scopes WHERE user_id=$1"

    query_res = await db_con.fetch(query, account_id)
    scope = [row["scope"] for row in query_res]
    return scope


async def create_new_tokens(db_con, userid, customer_id, scopes, account_type):
    refresh_scope = [Scopes.REFRESH]

    # create new tokens
    access = create_token(
        userid=userid, customer_id=customer_id, scopes=scopes, account_type=account_type, refresh=False
    )
    # refresh token does not need any scope, so just set it to refresh
    refresh = create_token(
        userid=userid, customer_id=customer_id, scopes=refresh_scope, account_type=account_type, refresh=True
    )

    # insert refresh token into DB
    if account_type == "customer":
        update_query = "UPDATE customers SET refresh_token=$1 WHERE id=$2"
    else:
        update_query = "UPDATE users SET refresh_token=$1 WHERE id=$2"

    await db_con.execute(update_query, refresh.token, userid)

    # return token model
    return AuthTokens(access=access, refresh=refresh)
