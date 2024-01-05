import re
from typing import Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, SecretStr, Field
from pydantic import constr, field_validator
from auth import AuthTokens, Scopes, ScopeConverter

USERNAME_MIN_LEN = 3
USERNAME_MAX_LEN = 32
USERNAME_VALID_SPECIAL_CHARS = "_.+-"  # make sure that - is that last char so the regexes work
USERNAME_REGEX_STR = f"^[a-zA-Z]+[a-zA-Z0-9{USERNAME_VALID_SPECIAL_CHARS}]+$"

PASSWORD_REGEX = r"""(
    ^(?=.*[A-Z])
    (?=.*[a-z])
    (?=.*[!@#$%^&*()~`|<>,.+=_"':;?/\\\[\]\{\}-])
    (?=.*[0-9])
    .{10,}
    $)"""


class AdminLogin(BaseModel):
    email: EmailStr
    password: SecretStr
    service: str | None = Field(
        default=None
    )  # TODO decide how to check usage for multiple products for a customer login
    client_type: str | None = Field(default=None)


class UserLogin(BaseModel):
    customer_id: UUID | str = Field(union_mode="left_to_right")
    username: str
    password: SecretStr
    service: str | None = Field(default=None)  # TODO remove after this key is removed from MA login request
    client_type: str | None = Field(default=None)


class PasswordModel(BaseModel):
    password1: SecretStr
    password2: SecretStr
    verify: bool | None = Field(default=None)

    @field_validator("password1")
    def password_requirements(cls, v):
        valid = re.compile(PASSWORD_REGEX, re.VERBOSE)

        assert valid.search(
            v.get_secret_value()
        ), "Password must contain at least one uppercase, one lowercase, one number, one special character, and be at least ten characters long"
        return v

    @field_validator("password2")
    def passwords_match(cls, v, values, **kwargs):
        if pw1 := values.data.get("password1"):
            assert v.get_secret_value() == pw1.get_secret_value(), "Passwords do not match"

        return v


class AdminCreate(ScopeConverter):
    email: EmailStr
    scopes: list[Scopes]


class UserCreate(ScopeConverter):
    email: EmailStr
    username: str
    scopes: list[Scopes]

    @field_validator("username")
    def username_alphanumeric(cls, v):
        assert len(v) >= USERNAME_MIN_LEN, "Username does not meet min length"
        assert len(v) <= USERNAME_MAX_LEN, "Username exceeds max length"

        assert v[0].isalpha(), "Username must start with a letter"
        assert v[-1].isalnum(), "Username must end with a letter or number"

        assert re.match(
            USERNAME_REGEX_STR, v
        ), f"Username can only contain letters, numbers, and these special characters: {USERNAME_VALID_SPECIAL_CHARS}"
        assert not re.findall(
            f"[{USERNAME_VALID_SPECIAL_CHARS}]{{2,}}", v
        ), "Username cannot contain consecutive special characters"

        return v


class UserProfile(BaseModel):
    username: constr(min_length=USERNAME_MIN_LEN, max_length=USERNAME_MAX_LEN, pattern=USERNAME_REGEX_STR)
    email: EmailStr
    user_id: str
    scopes: list[Scopes]


class AdminProfile(BaseModel):
    email: EmailStr
    user_id: str
    scopes: list[Scopes]


class AccountUpdateAction(BaseModel):
    action_type: str
    new_alias: str | None = Field(default=None)


class UserScopesUpdate(ScopeConverter):
    scopes: list[Scopes]


class UnableToUpdateAccountResponse(BaseModel):
    message: str


class UsageQuota(BaseModel):
    current: dict[str, Any]
    limits: dict[str, Any]
    jobs_reached: bool
    uploads_reached: bool


class LoginResponse(BaseModel):
    tokens: AuthTokens
    usage_quota: UsageQuota | None = Field(default=None)
    user_scopes: dict[Scopes, Scopes | None] | None = Field(default=None)
    admin_scopes: dict[Scopes, Scopes | None] | None = Field(default=None)


class PreferencesUpdate(BaseModel):
    product: str
    changes: dict[str, Any]
