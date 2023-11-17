from typing import Any

from pydantic import BaseModel


# REQUESTS


# TODO add serial number validation?
class SerialNumberRequest(BaseModel):
    hw_version: str
    serial_number: str


class MainFirmwareUploadRequest(BaseModel):
    version: str
    is_compatible_with_current_ma_sw: bool
    is_compatible_with_current_sting_sw: bool
    md5s: str


class ChannelFirmwareUploadRequest(BaseModel):
    version: str
    main_fw_version: str
    hw_version: str
    md5s: str


# RESPONSES


class MantarrayUnitsResponse(BaseModel):
    units: list[dict[str, str]]


class FirmwareInfoResponse(BaseModel):
    main_fw_info: list[dict[str, str]]
    channel_fw_info: list[dict[str, str]]


class FirmwareUploadResponse(BaseModel):
    params: dict[str, Any]
