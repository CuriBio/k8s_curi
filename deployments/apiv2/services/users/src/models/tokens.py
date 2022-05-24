from pydantic import BaseModel

from auth import Token


class AuthTokens(BaseModel):
    access: Token
    refresh: Token

    # @validator("access")
    # def _access_requirements(cls, v):
    #     assert not v.refresh
    #     return v

    # @validator("refresh")
    # def _refresh_requirements(cls, v):
    #     assert v.refresh
    #     return v
