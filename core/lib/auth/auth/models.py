from typing import List
from pydantic import BaseModel

class JWTMeta(BaseModel):
    iss: str = "curibio.com"
    aud: str
    iat: float
    exp: float
    scope: List[str] = []


class JWTDetails(BaseModel):
    """How we'll identify users"""
    userid: str 


class JWTPayload(JWTMeta, JWTDetails):
    pass


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"

