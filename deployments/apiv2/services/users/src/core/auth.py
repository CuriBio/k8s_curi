import jwt
from typing import List

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from core.config import JWT_ALGORITHM, JWT_SECRET_KEY, JWT_AUDIENCE

security = HTTPBearer()

class ProtectedAny:
    def __init__(self, scope: List[str] = ["users:free"]):
        self.scope = set(scope)

    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(security)):
        token = credentials.credentials

        try:
            payload = jwt.decode(
                token,
                key=str(JWT_SECRET_KEY),
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
