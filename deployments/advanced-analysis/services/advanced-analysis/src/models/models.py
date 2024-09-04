from datetime import datetime
from pydantic import BaseModel
from typing import Any
import uuid


# REQUESTS


class PostAdvancedAnalysesRequest(BaseModel):
    version: str
    output_name: str
    sources: list[uuid.UUID]

    platemap_overrides: dict[str, Any]

    # analysis params
    experiment_start_time_utc: datetime
    local_tz_offset_hours: int


class PostAdvancedAnalysesDownloadRequest(BaseModel):
    job_ids: list[uuid.UUID]


# RESPONSES


class _AdvancedAnalysisJobInfo(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    created_at: datetime
    sources: list[uuid.UUID]
    meta: str
    status: str


GetAdvancedAnalysesResponse = list[_AdvancedAnalysisJobInfo]


class _Limits(BaseModel):
    jobs: int
    expiration_date: datetime | None


class _Current(BaseModel):
    jobs: int


class GetAdvancedAnalysisUsageResponse(BaseModel):
    limits: _Limits
    current: _Current
