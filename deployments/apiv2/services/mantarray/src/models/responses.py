from pydantic import BaseModel


# REQUESTS


# TODO add serial number validation?
class SerialNumberRequest(BaseModel):
    hw_version: str
    serial_number: str


# RESPONSES


class MantarrayUnitsResponse(BaseModel):
    units: list[dict[str, str]]
