from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union
import uuid

from .types import Number, TupleParam


class UploadRequest(BaseModel):
    filename: str
    md5s: Optional[str]
    upload_type: str


class UploadResponse(BaseModel):
    id: Optional[uuid.UUID]
    params: Dict[str, Any]


class JobRequest(BaseModel):
    upload_id: uuid.UUID
    version: str

    normalize_y_axis: Optional[bool]

    stiffness_factor: Optional[int]
    inverted_post_magnet_wells: Optional[List[str]]

    baseline_widths_to_use: Optional[TupleParam]
    max_y: Optional[Number]
    peaks_valleys: Optional[Dict[str, List[List[Number]]]]

    twitch_widths: Optional[List[int]]
    start_time: Optional[Number]
    end_time: Optional[Number]

    prominence_factors: Optional[TupleParam]
    width_factors: Optional[TupleParam]


class JobResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    upload_id: uuid.UUID
    status: str
    priority: int


class DownloadItem(BaseModel):
    jobId: uuid.UUID
    uploadId: uuid.UUID
    analyzedFile: str
    datetime: str
    status: str
    analysisParams: Dict[Any, Any]


class WaveformDataResponse(BaseModel):
    coordinates: Dict[str, List[Any]]
    peaks_valleys: Dict[str, List[Any]]


class JobDownloadRequest(BaseModel):
    job_ids: List[uuid.UUID]


class UploadDownloadRequest(BaseModel):
    upload_ids: List[uuid.UUID]


class GenericErrorResponse(BaseModel):
    error: Union[str, Dict[str, bool]]
    type: str
