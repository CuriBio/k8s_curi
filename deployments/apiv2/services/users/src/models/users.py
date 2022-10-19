import re
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, SecretStr
from pydantic import constr, validator


class CustomerLogin(BaseModel):
    email: EmailStr
    password: SecretStr


class UserLogin(BaseModel):
    customer_id: UUID
    username: str
    password: SecretStr
    service: str


class CustomerCreate(BaseModel):
    email: EmailStr
    password1: SecretStr
    password2: SecretStr
    # adding this attr and its validator to force /register to use UserCreate if a username is given
    username: Optional[str]

    @validator("password1")
    def password_requirements(cls, v):
        valid = re.compile(
            r"""(
                ^(?=.*[A-Z])
                (?=.*[a-z])
                (?=.*[!@#$%^&*><?_=+~-])
                (?=.*[0-9])
                .{10,}
                $)""",
            re.VERBOSE,
        )

        assert valid.search(
            v.get_secret_value()
        ), "Password must contain at least one uppercase, one lowercase, one number, one special character, and be at least ten characters long"
        return v

    @validator("password2")
    def passwords_match(cls, v, values, **kwargs):
        if pw1 := values.get("password1"):
            assert v.get_secret_value() == pw1.get_secret_value(), "Passwords do not match"

        return v

    @validator("username")
    def username_alphanumeric(cls, v):
        assert v is None
        return v


USERNAME_MIN_LEN = 3
USERNAME_MAX_LEN = 32
USERNAME_VALID_SPECIAL_CHARS = "_.+-"  # make sure that - is that last char so the regexes work
USERNAME_REGEX_STR = f"^[a-zA-Z]+[a-zA-Z0-9{USERNAME_VALID_SPECIAL_CHARS}]+$"


class UserCreate(CustomerCreate):
    username: str
    service: str

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
    scope: list


class CustomerProfile(BaseModel):
    email: EmailStr
    user_id: str
    scope: list


class UserAction(BaseModel):
    action_type: str
