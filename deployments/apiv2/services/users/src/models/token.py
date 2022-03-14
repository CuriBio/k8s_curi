from typing import List
from calendar import timegm
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
from core.config import JWT_AUDIENCE, ACCESS_TOKEN_EXPIRE_MINUTES


class JWTMeta(BaseModel):
    iss: str = "curibio.com"
    aud: str = JWT_AUDIENCE
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

