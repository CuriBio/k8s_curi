from uuid import UUID
import jwt
from datetime import datetime, timezone, timedelta
from calendar import timegm
from typing import List

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import JWTMeta, JWTDetails, JWTPayload, Token
from .settings import (
    JWT_SECRET_KEY,
    JWT_AUDIENCE,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_MINUTES,
)


security = HTTPBearer()


class ProtectedAny:
    def __init__(self, scope: List[str] = ["users:free"]):
        self.scope = set(scope)

    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        token = credentials.credentials

        try:
            payload = jwt.decode(
                token, key=str(JWT_SECRET_KEY), algorithms=JWT_ALGORITHM, audience=JWT_AUDIENCE
            )
            payload_scopes = set(payload.get("scope", []))
            if not self.scope.intersection(payload_scopes):
                raise Exception()

            return payload

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authenticated user.",
                headers={"WWW-Authenticate": "Bearer"},
            )


def create_token(*, scope: List[str], userid: UUID, refresh=False):
    exp_dur = REFRESH_TOKEN_EXPIRE_MINUTES if refresh else ACCESS_TOKEN_EXPIRE_MINUTES

    iat = timegm(datetime.now(tz=timezone.utc).utctimetuple())
    exp = timegm((datetime.now(tz=timezone.utc) + timedelta(minutes=exp_dur)).utctimetuple())

    jwt_meta = JWTMeta(aud=JWT_AUDIENCE, scope=scope, iat=iat, exp=exp, refresh=refresh)
    jwt_details = JWTDetails(userid=userid.hex)
    jwt_payload = JWTPayload(**jwt_meta.dict(), **jwt_details.dict())

    jwt_token = jwt.encode(payload=jwt_payload.dict(), key=str(JWT_SECRET_KEY), algorithm=JWT_ALGORITHM)
    return Token(token=jwt_token)
