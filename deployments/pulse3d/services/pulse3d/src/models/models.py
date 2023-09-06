from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union
import uuid

from .types import Number, TupleParam


class UploadRequest(BaseModel):
    filename: str
    md5s: Optional[str]
    upload_type: str
    # default to True to preserve backwards compatibility with older MA controller versions
    auto_upload: Optional[bool] = True


class UsageQuota(BaseModel):
    current: Dict[str, Any]
    limits: Dict[str, Any]
    jobs_reached: bool
    uploads_reached: bool


class UploadResponse(BaseModel):
    id: Optional[uuid.UUID]
    params: Dict[str, Any]


class JobRequest(BaseModel):
    upload_id: uuid.UUID

    version: str
    previous_version: Optional[str]

    name_override: Optional[str]

    data_type: Optional[str]

    well_groups: Optional[Dict[str, List[str]]]

    normalize_y_axis: Optional[bool]
    max_y: Optional[Number]

    stim_waveform_format: Optional[str]
    include_stim_protocols: Optional[bool]

    stiffness_factor: Optional[int]
    inverted_post_magnet_wells: Optional[List[str]]

    baseline_widths_to_use: Optional[TupleParam]
    twitch_widths: Optional[List[int]]
    peaks_valleys: Optional[Dict[str, List[List[Number]]]]

    start_time: Optional[Number]
    end_time: Optional[Number]

    # shared peak finding params
    width_factors: Optional[TupleParam]
    # old peak finding params
    prominence_factors: Optional[TupleParam]
    # noise based peak finding params
    relative_prominence_factor: Optional[Number]
    noise_prominence_factor: Optional[Number]
    height_factor: Optional[Number]
    max_frequency: Optional[Number]
    valley_search_duration: Optional[Number]
    upslope_duration: Optional[Number]
    upslope_noise_allowance_duration: Optional[Number]


class SavePresetRequest(BaseModel):
    name: str
    analysis_params: Dict[str, Any]


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
    analysisParams: Dict[Any, Any]


class WaveformDataResponse(BaseModel):
    time_force_url: str
    peaks_valleys_url: str
    data_type: str


class JobDownloadRequest(BaseModel):
    job_ids: List[uuid.UUID]


class UploadDownloadRequest(BaseModel):
    upload_ids: List[uuid.UUID]


class GenericErrorResponse(BaseModel):
    message: Union[str, UsageQuota, Dict[str, bool]]
    error: str
