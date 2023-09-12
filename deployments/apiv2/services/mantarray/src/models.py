from pydantic import BaseModel


# REQUESTS


# RESPONSES


class MantarrayUnitsResponse(BaseModel):
    units: list[dict[str, str]]
