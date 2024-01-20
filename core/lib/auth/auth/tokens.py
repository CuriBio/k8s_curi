from calendar import timegm
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
import logging
from hashlib import sha256

from pydantic import BaseModel
from fastapi import HTTPException, Depends, status, Cookie
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from .models import AccountTypes, JWTMeta, JWTDetails, JWTPayload, Token
from .settings import (
    JWT_SECRET_KEY,
    JWT_AUDIENCE,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_MINUTES,
    EMAIL_VER_TOKEN_EXPIRE_MINUTES,
)
from .scopes import ScopeTags, Scopes, convert_scope_str

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

    async def __call__(
        self,
        fingerprint: str | None = Cookie(None),
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ):
        token = credentials.credentials

        try:
            payload = decode_token(token)
            payload_scopes = set(payload.scopes)

            # allowing fingerprint to be None to prevent 422 errors, handle ourselves instead to return 401
            # if there is no fingerprint, it means no cookie was sent in request and needs to be rejected immediately
            # no cookie will be sent with account scopes for verifying accounts and sending emails
            account_scopes = [s for s in payload_scopes if ScopeTags.ACCOUNT in s.tags]

            if fingerprint is None and not account_scopes:
                raise Exception("Required cookie not present with request")
            # the JWT fingerprint must match that found in the cookie, otherwise reject
            if fingerprint is not None and payload.fingerprint != sha256(fingerprint.encode()).hexdigest():
                raise Exception("Fingerprints do not match")

            # make sure that the access token has the required scope
            if not self.scopes & payload_scopes:
                # TODO raise a specific exeption here so that other errors result in a 500?
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
    return JWTPayload(
        **jwt.decode(token, key=str(JWT_SECRET_KEY), algorithms=JWT_ALGORITHM, audience=JWT_AUDIENCE)
    )


def create_token(
    *,
    userid: UUID | None,
    customer_id: UUID,
    scopes: list[Scopes],
    account_type: AccountTypes,
    fingerprint: str = "",  # has to empty string for encoding
    refresh: bool = False,
):
    # make sure tokens have at least 1 scope
    if not scopes:
        raise ValueError("Tokens must have at least 1 scope")

    # TODO remove this once all calls use AccountTypes enum
    # make sure account type is valid
    if account_type not in ("user", "admin"):
        raise ValueError(f"Valid account types are 'user' and 'admin', not '{account_type}'")

    # TODO remove this after testing?
    if not customer_id:
        raise ValueError("All tokens must have a customer ID")

    # make sure if there account scopes that it is the only scope present
    account_scopes = [s for s in scopes if ScopeTags.ACCOUNT in s.tags]
    if account_scopes and len(scopes) != 1:
        raise ValueError("If an account scope is present, it must be the only scope present")

    if not account_scopes and not fingerprint:
        raise ValueError("Fingerprint required for token type")

    if fingerprint:
        # TODO make this a separate util?
        fingerprint = sha256(fingerprint.encode()).hexdigest()

    # make sure no invalid scopes or fields based on account type
    if account_type == AccountTypes.USER:
        # make sure a user is not given admin privileges
        if account_scopes:
            if admin_account_scopes := [s for s in account_scopes if "admin" in s]:
                raise ValueError(f"User tokens cannot have scopes '{admin_account_scopes}'")
        elif admin_scopes := {s for s in scopes if ScopeTags.ADMIN in s.tags}:
            raise ValueError(f"User tokens cannot have scopes '{list(admin_scopes)}'")
        if not userid:
            raise ValueError("User tokens must have a user ID")
        userid = userid.hex
    if account_type == AccountTypes.ADMIN:
        if userid:
            raise ValueError("Admin tokens cannot have a user ID")
        # make sure admin only has admin scopes
        if account_scopes:
            if non_admin_account_scopes := [s for s in account_scopes if "admin" not in s]:
                raise ValueError(f"Admin tokens cannot have scopes '{non_admin_account_scopes}'")
        elif non_admin_scopes := set(s for s in scopes if ScopeTags.ADMIN not in s.tags) - {Scopes.REFRESH}:
            raise ValueError(f"Admin tokens cannot have scopes '{list(non_admin_scopes)}'")
    # make sure no invalid scopes or fields based on token type
    if refresh:
        if non_refresh_scopes := set(scopes) - {Scopes.REFRESH}:
            raise ValueError(f"Invalid scopes for refresh token {list(non_refresh_scopes)}")
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
    jwt_details = JWTDetails(
        customer_id=customer_id.hex, userid=userid, account_type=account_type, fingerprint=fingerprint
    )
    jwt_payload = JWTPayload(**jwt_meta.model_dump(), **jwt_details.model_dump())

    jwt_token = jwt.encode(payload=jwt_payload.model_dump(), key=str(JWT_SECRET_KEY), algorithm=JWT_ALGORITHM)

    return Token(token=jwt_token)


# TODO add testing for all this
async def get_account_scopes(db_con, account_id, is_admin_account):
    if is_admin_account:
        query = "SELECT scope FROM account_scopes WHERE customer_id=$1 AND user_id IS NULL"
    else:
        query = "SELECT scope FROM account_scopes WHERE user_id=$1"

    query_res = await db_con.fetch(query, account_id)
    scope = [convert_scope_str(row["scope"]) for row in query_res]
    return scope


# TODO make sure all calls to this use AccountTypes
async def get_user_authorization(db_con, userid, customer_id, scopes, account_type) -> tuple[AuthTokens, str]:
    refresh_scope = [Scopes.REFRESH]
    fingerprint = str(uuid4())
    # create new tokens
    access = create_token(
        userid=userid,
        customer_id=customer_id,
        scopes=scopes,
        account_type=account_type,
        fingerprint=fingerprint,
        refresh=False,
    )
    # refresh token does not need any scope, so just set it to refresh
    refresh = create_token(
        userid=userid,
        customer_id=customer_id,
        scopes=refresh_scope,
        account_type=account_type,
        fingerprint=fingerprint,
        refresh=True,
    )

    # TODO should probably split this part out into its own function
    # insert refresh token into DB
    if account_type == AccountTypes.ADMIN:
        account_id = customer_id
        update_query = "UPDATE customers SET refresh_token=$1 WHERE id=$2"
    else:
        account_id = userid
        update_query = "UPDATE users SET refresh_token=$1 WHERE id=$2"

    await db_con.execute(update_query, refresh.token, account_id)

    # return token model
    return AuthTokens(access=access, refresh=refresh), fingerprint
