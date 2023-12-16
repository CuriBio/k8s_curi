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


class ChannelFirmwareUpdateRequest(BaseModel):
    main_fw_version: str


# RESPONSES


class MantarrayUnitsResponse(BaseModel):
    units: list[dict[str, str]]


class FirmwareInfoResponse(BaseModel):
    main_fw_info: list[dict[str, Any]]
    channel_fw_info: list[dict[str, Any]]


class FirmwareUploadResponse(BaseModel):
    params: dict[str, Any]


class LatestVersionsResponse(BaseModel):
    ma_sw: str
    sting_sw: str
    main_fw: str
    channel_fw: str
