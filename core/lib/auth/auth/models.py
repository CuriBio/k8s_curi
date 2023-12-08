from pydantic import BaseModel
from .scopes import ScopeConverter, Scopes


class JWTMeta(ScopeConverter):
    iss: str = "curibio.com"
    aud: str
    iat: float
    exp: float
    scopes: list[Scopes]
    refresh: bool = False


class JWTDetails(BaseModel):
    """How we'll identify users and customers"""

    customer_id: str | None
    userid: str
    account_type: str


class JWTPayload(JWTMeta, JWTDetails):
    pass


class Token(BaseModel):
    token: str
    token_type: str = "bearer"
