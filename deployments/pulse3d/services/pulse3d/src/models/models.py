from pydantic import BaseModel
from typing import Any
import uuid

from .types import Number, TupleParam


class UploadRequest(BaseModel):
    filename: str
    md5s: str | None  # TODO when would this be None?
    upload_type: str
    # default to True to preserve backwards compatibility with older MA controller versions
    auto_upload: bool | None = True


class UsageQuota(BaseModel):
    current: dict[str, Any]
    limits: dict[str, Any]
    jobs_reached: bool
    uploads_reached: bool


class UploadResponse(BaseModel):
    id: uuid.UUID | None
    params: dict[str, Any]


class JobRequest(BaseModel):
    upload_id: uuid.UUID

    version: str
    previous_version: str | None

    name_override: str | None

    data_type: str | None

    well_groups: dict[str, list[str]] | None

    normalize_y_axis: bool | None
    max_y: Number | None

    stim_waveform_format: str | None
    include_stim_protocols: bool | None

    stiffness_factor: int | None
    inverted_post_magnet_wells: list[str] | None

    baseline_widths_to_use: TupleParam | None
    twitch_widths: list[int] | None
    peaks_valleys: dict[str, list[list[Number]]] | None

    start_time: Number | None
    end_time: Number | None

    # shared peak finding params
    width_factors: TupleParam | None
    # old peak finding params
    prominence_factors: TupleParam | None
    # noise based peak finding params
    relative_prominence_factor: Number | None
    noise_prominence_factor: Number | None
    height_factor: Number | None
    max_frequency: Number | None
    valley_search_duration: Number | None
    upslope_duration: Number | None
    upslope_noise_allowance_duration: Number | None


class SavePresetRequest(BaseModel):
    name: str
    analysis_params: dict[str, Any]


class JobResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    upload_id: uuid.UUID
    status: str
    priority: int
    usage_quota: UsageQuota


class DownloadItem(BaseModel):
    jobId: uuid.UUID
    uploadId: uuid.UUID
    analyzedFile: str
    datetime: str
    status: str
    analysisParams: dict[Any, Any]


class WaveformDataResponse(BaseModel):
    time_force_url: str
    peaks_valleys_url: str
    amplitude_label: str


class JobDownloadRequest(BaseModel):
    job_ids: list[uuid.UUID]


class UploadDownloadRequest(BaseModel):
    upload_ids: list[uuid.UUID]


class GenericErrorResponse(BaseModel):
    message: str | UsageQuota | dict[str, bool]
    error: str
