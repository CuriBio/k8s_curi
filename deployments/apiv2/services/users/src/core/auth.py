import jwt
from typing import List

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.config import Config
from starlette.datastructures import Secret

security = HTTPBearer()

class ProtectedAny:
    def __init__(self, scope: List[str] = ["users:free"]):
        self.scope = set(scope)

    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        token = credentials.credentials

        try:
            payload = jwt.decode(
                token,
                key=str(config(JWT_SECRET_KEY, cast=Secret)),
                algorithms=JWT_ALGORITHM,
                audience=JWT_AUDIENCE,
            )
            payload_scopes = set(payload.get("scope", []))
            if not self.scope.intersection(payload_scopes):
                raise Exception()

            return payload

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authenticated user.",
                headers={"WWW-Authenticate": "Bearer"},
            )
