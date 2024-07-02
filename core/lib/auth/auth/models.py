from enum import auto, StrEnum
from pydantic import BaseModel
from .scopes import ScopeConverter, Scopes


class AccountTypes(StrEnum):
    ADMIN = auto()
    USER = auto()


class LoginType(StrEnum):
    PASSWORD = auto()
    SSO_MICROSOFT = auto()


class JWTMeta(ScopeConverter):
    iss: str = "curibio.com"
    aud: str
    iat: float
    exp: float
    scopes: list[Scopes]
    refresh: bool = False


class JWTDetails(BaseModel):
    """How we'll identify users and admins"""

    customer_id: str
    userid: str | None  # None for admin accounts
    account_type: AccountTypes
    login_type: LoginType = LoginType.PASSWORD

    @property
    def account_id(self):
        return self.customer_id if self.account_type == AccountTypes.ADMIN else self.userid


class JWTPayload(JWTMeta, JWTDetails):
    pass


class Token(BaseModel):
    token: str
    token_type: str = "bearer"
