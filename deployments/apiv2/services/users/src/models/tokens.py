from pydantic import BaseModel

from auth import Token


class LoginResponse(BaseModel):
    access: Token
    refresh: Token

    # @validator("token")
    # def _token_requirements(cls, v):
    #     assert not v.refresh
    #     return v

    # @validator("refresh")
    # def _refresh_requirements(cls, v):
    #     assert v.refresh
    #     return v
