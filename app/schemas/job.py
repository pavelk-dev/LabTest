from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class JobCreate(BaseModel):
    test_definition_id: UUID
    rf_scene_definition_id: UUID | None = None
    yaml_snapshot: str


class JobResponse(BaseModel):
    id: UUID
    status: str

class JobLogResponse(BaseModel):
    timestamp: datetime
    level: str
    message: str


class ResultResponse(BaseModel):
    metric: str
    numeric_value: float | None = None
    text_value: str | None = None
    unit: str | None = None


class JobDetailResponse(BaseModel):
    id: UUID
    status: str
    logs: list[JobLogResponse]
    results: list[ResultResponse]