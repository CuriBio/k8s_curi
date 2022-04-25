import re
from typing import Optional

from pydantic import BaseModel, EmailStr, SecretStr
from pydantic import constr, validator


class UserLogin(BaseModel):
    customer_id: Optional[str]
    username: str
    password: SecretStr


class UserCreate(BaseModel):
    username: constr(min_length=5, max_length=64, regex="^[a-zA-Z]+[a-zA-Z0-9-_]+$")
    password1: SecretStr
    password2: SecretStr
    email: EmailStr

    @validator("username")
    def username_alphanumeric(cls, v):
        assert v.isalnum(), "username must be alphanumeric"
        return v

    @validator("password1")
    def password_requirements(cls, v):
        valid = re.compile(
            r"""(
                ^(?=.*[A-Z])
                (?=.*[a-z])
                (?=.*[!@#$%^&*><?-_=+~])
                (?=.*[0-9])
                .{10,}
                $)""",
            re.VERBOSE,
        )

        assert valid.search(v.get_secret_value()), "password does not meet minimum requirements"
        return v

    @validator("password2")
    def passwords_match(cls, v, values, **kwargs):
        p2 = v.get_secret_value()
        if "password1" in values and p2 != values["password1"].get_secret_value():
            raise ValueError("passwords do not match")
        return v


class UserProfile(BaseModel):
    username: constr(min_length=5, max_length=64, regex="^[a-zA-Z]+[a-zA-Z0-9-_]+$")
    email: EmailStr
    user_id: str
    account_type: str
    scope: list
