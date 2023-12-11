from enum import auto, StrEnum
from pydantic import BaseModel
from .scopes import ScopeConverter, Scopes


class AccountTypes(StrEnum):
    CUSTOMER = auto()
    USER = auto()


class JWTMeta(ScopeConverter):
    iss: str = "curibio.com"
    aud: str
    iat: float
    exp: float
    scopes: list[Scopes]
    refresh: bool = False


class JWTDetails(BaseModel):
    """How we'll identify users and customers"""

    customer_id: str
    userid: str | None  # None for admin accounts
    account_type: AccountTypes

    @property
    def account_id(self):
        return self.customer_id if self.account_type == AccountTypes.CUSTOMER else self.userid


class JWTPayload(JWTMeta, JWTDetails):
    pass


class Token(BaseModel):
    token: str
    token_type: str = "bearer"
