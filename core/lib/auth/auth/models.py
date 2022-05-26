from typing import List
from pydantic import BaseModel


class JWTMeta(BaseModel):
    iss: str = "curibio.com"
    aud: str
    iat: float
    exp: float
    scope: List[str]
    refresh: bool = False


class JWTDetails(BaseModel):
    """How we'll identify users and customers"""

    userid: str
    account_type: str


class JWTPayload(JWTMeta, JWTDetails):
    pass


class Token(BaseModel):
    token: str
    token_type: str = "bearer"
