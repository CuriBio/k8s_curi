from pydantic import BaseModel


# REQUESTS


class SerialNumberRequest(BaseModel):
    hw_version: str
    serial_number: str


# RESPONSES


class MantarrayUnitsResponse(BaseModel):
    units: list[dict[str, str]]
