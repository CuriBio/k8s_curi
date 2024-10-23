from enum import auto, StrEnum
from fastapi import Query
from pydantic import BaseModel, Field
from typing import Any
import datetime
import uuid

from pulse3D.data_loader.metadata import NormalizationMethods

from .types import Number, TupleParam


class NotificationType(StrEnum):
    CUSTOMERS_AND_USERS = auto()
    CUSTOMERS = auto()
    USERS = auto()


class SaveNotificationRequest(BaseModel):
    subject: str
    body: str
    notification_type: NotificationType = NotificationType.CUSTOMERS_AND_USERS


class SaveNotificationResponse(BaseModel):
    id: uuid.UUID


class ViewNotificationMessageRequest(BaseModel):
    id: uuid.UUID


class ViewNotificationMessageResponse(BaseModel):
    viewed_at: datetime.datetime | None = None


class NotificationResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime.datetime
    subject: str
    body: str
    notification_type: NotificationType = NotificationType.CUSTOMERS_AND_USERS


class NotificationMessageResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime.datetime
    viewed_at: datetime.datetime | None = None
    subject: str
    body: str


class UploadRequest(BaseModel):
    filename: str
    md5s: str | None = Field(default=None)  # TODO when would this be None?
    upload_type: str
    # default to True to preserve backwards compatibility with older MA controller versions
    auto_upload: bool | None = Field(default=True)


class GetJobsInfoRequest(BaseModel):
    upload_ids: list[uuid.UUID]
    upload_type: str | None = Field(default=None)


class GetJobsRequest(BaseModel):
    job_ids: list[uuid.UUID] | None = Field(Query(None))
    # legacy options
    legacy: bool = True
    download: bool = True
    # new options
    upload_type: str | None = None
    include_prerelease_versions: bool = True
    version_min: str | None = None
    version_max: str | None = None
    status: str | None = None
    filename: str | None = None
    sort_field: str | None = None
    sort_direction: str | None = None
    skip: int = 0
    limit: int = 300


class UsageQuota(BaseModel):
    current: dict[str, Any]
    limits: dict[str, Any]
    jobs_reached: bool
    uploads_reached: bool


class UploadResponse(BaseModel):
    id: uuid.UUID | None = Field(default=None)  # None for log uploads
    params: dict[str, Any]


class JobRequest(BaseModel):
    upload_id: uuid.UUID

    version: str  # this should not ever have an rc component
    previous_version: str | None = Field(default=None)

    name_override: str | None = Field(default=None)

    normalize_y_axis: bool | None = Field(default=None)
    max_y: Number | None = Field(default=None)

    # metrics
    well_groups: dict[str, list[str]] | None = Field(default=None)
    baseline_widths_to_use: TupleParam | None = Field(default=None)
    twitch_widths: list[int] | None = Field(default=None)
    start_time: Number | None = Field(default=None)
    end_time: Number | None = Field(default=None)
    relaxation_search_limit_secs: Number | None = Field(default=None)

    # shared peak finding params
    width_factors: TupleParam | None = Field(default=None)
    # old peak finding params
    prominence_factors: TupleParam | None = Field(default=None)
    # noise based peak finding params
    relative_prominence_factor: Number | None = Field(default=None)
    noise_prominence_factor: Number | None = Field(default=None)
    height_factor: Number | None = Field(default=None)
    max_frequency: Number | None = Field(default=None)
    valley_search_duration: Number | None = Field(default=None)
    upslope_duration: Number | None = Field(default=None)
    upslope_noise_allowance_duration: Number | None = Field(default=None)

    # IA params
    peaks_valleys: dict[str, list[list[Number]]] | None = Field(default=None)
    timepoints: list[Number] | None = Field(default=None)  # not used for pulse3d versions < 1.0.0

    # MA params
    stim_waveform_format: str | None = Field(default=None)
    include_stim_protocols: bool | None = Field(default=None)
    stiffness_factor: int | None = Field(default=None)
    inverted_post_magnet_wells: list[str] | None = Field(default=None)
    # nautilai params
    data_type: str | None = Field(default=None)
    normalization_method: NormalizationMethods | None = Field(default=None)
    detrend: bool | None = Field(default=None)


class SavePresetRequest(BaseModel):
    name: str
    analysis_params: dict[str, Any]
    upload_type: str


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
    upload_type: str | None = Field(default=None)
    job_ids: list[uuid.UUID]
    timezone: str | None = Field(default=None)


class UploadDownloadRequest(BaseModel):
    upload_type: str | None = Field(default=None)
    upload_ids: list[uuid.UUID]


class GenericErrorResponse(BaseModel):
    message: str | UsageQuota | dict[str, bool]
    error: str
