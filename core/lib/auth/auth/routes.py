from calendar import timegm
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

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


security = HTTPBearer()


class ProtectedAny:
    def __init__(self, scope: List[str] = ["pulse3d:paid"], refresh: bool = False, check_scope: bool = True):
        # don't check scope if using this for refresh tokens
        if refresh:
            check_scope = False

        self.scope = set(scope)
        self.refresh = refresh
        # Tanner (5/24/22): currently /refresh and /logout don't have any required scope,
        # so don't need to check the scope of tokens that they receive
        self.check_scope = check_scope

    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        token = credentials.credentials

        try:
            payload = decode_token(token)
            payload_scopes = set(payload["scope"])

            # check if the wrong type of token was given
            if payload["refresh"] != self.refresh:
                raise Exception()

            # if checking scope, make sure that the access token has the required scope
            if self.check_scope and not self.scope.intersection(payload_scopes):
                raise Exception()

            return payload

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authenticated user.",
                headers={"WWW-Authenticate": "Bearer"},
            )


def decode_token(token: str):
    return jwt.decode(token, key=str(JWT_SECRET_KEY), algorithms=JWT_ALGORITHM, audience=JWT_AUDIENCE)


def create_token(
    *, userid: UUID, customer_id: Optional[UUID], scope: List[str], account_type: str, refresh: bool = False
):
    # make sure tokens have at least 1 scope
    if not scope:
        raise ValueError("Tokens must have at least 1 scope")
    # make sure account type is valid
    if account_type not in ("user", "customer"):
        raise ValueError(f"Valid account types are 'user' and 'customer', not '{account_type}'")
    if account_type == "user":
        # make sure a user is not given admin privileges
        if any("customer" in s for s in scope):
            raise ValueError(f"User tokens cannot have scope '{scope}'")
        if not customer_id:
            raise ValueError("User tokens must have a customer ID")
        customer_id = customer_id.hex
    if account_type == "customer":
        if customer_id:
            raise ValueError("Customer tokens cannot have a customer ID")

    # three different constant exp times based on token type
    if refresh:
        exp_dur = REFRESH_TOKEN_EXPIRE_MINUTES  # 30min
    elif "users:verify" in scope:
        exp_dur = EMAIL_VER_TOKEN_EXPIRE_MINUTES  # 30min
    else:
        exp_dur = ACCESS_TOKEN_EXPIRE_MINUTES  # 5min

    now = datetime.now(tz=timezone.utc)
    iat = timegm(now.utctimetuple())
    exp = timegm((now + timedelta(minutes=exp_dur)).utctimetuple())
    jwt_meta = JWTMeta(aud=JWT_AUDIENCE, scope=scope, iat=iat, exp=exp, refresh=refresh)
    jwt_details = JWTDetails(customer_id=customer_id, userid=userid.hex, account_type=account_type)
    jwt_payload = JWTPayload(**jwt_meta.dict(), **jwt_details.dict())

    jwt_token = jwt.encode(payload=jwt_payload.dict(), key=str(JWT_SECRET_KEY), algorithm=JWT_ALGORITHM)

    return Token(token=jwt_token)


def split_scope_account_data(scope: str) -> Tuple[str, str]:
    # example: 'pulse3d:paid' 'pulse3d:free'

    split_scope = scope.split(":")
    service = split_scope[0]
    customer_tier = split_scope[-1]

    return service, customer_tier
