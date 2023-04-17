import re
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, SecretStr
from pydantic import constr, validator
from models.tokens import AuthTokens

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


class CustomerLogin(BaseModel):
    email: EmailStr
    password: SecretStr
    service: str
    client_type: Optional[str]


class UserLogin(BaseModel):
    customer_id: UUID
    username: str
    password: SecretStr
    service: str
    client_type: Optional[str]


class PasswordModel(BaseModel):
    password1: SecretStr
    password2: SecretStr
    verify: Optional[bool]

    @validator("password1")
    def password_requirements(cls, v):
        valid = re.compile(PASSWORD_REGEX, re.VERBOSE)

        assert valid.search(
            v.get_secret_value()
        ), "Password must contain at least one uppercase, one lowercase, one number, one special character, and be at least ten characters long"
        return v

    @validator("password2")
    def passwords_match(cls, v, values, **kwargs):
        if pw1 := values.get("password1"):
            assert v.get_secret_value() == pw1.get_secret_value(), "Passwords do not match"

        return v


class CustomerCreate(PasswordModel):
    email: EmailStr
    scope: List[str]


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    scope: Optional[List[str]]

    @validator("username")
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
    username: constr(min_length=USERNAME_MIN_LEN, max_length=USERNAME_MAX_LEN, regex=USERNAME_REGEX_STR)
    email: EmailStr
    user_id: str
    account_type: str
    scope: List[str]


class CustomerProfile(BaseModel):
    email: EmailStr
    user_id: str
    scope: List[str]


class UserAction(BaseModel):
    action_type: str


class UnableToUpdateAccountResponse(BaseModel):
    message: str


class UsageQuota(BaseModel):
    current: Dict[str, Any]
    limits: Dict[str, Any]
    jobs_reached: bool
    uploads_reached: bool


class LoginResponse(BaseModel):
    tokens: AuthTokens
    usage_quota: UsageQuota
