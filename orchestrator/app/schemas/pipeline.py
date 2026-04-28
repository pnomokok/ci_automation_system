from datetime import datetime

from pydantic import BaseModel, HttpUrl

from app.models.pipeline import PipelineStatus, TriggerType
from app.models.step import StepStatus


# ── Step (pipeline detayında nested gelir) ───────────────────────────────────

class StepResponse(BaseModel):
    id: str
    name: str
    order: int
    status: StepStatus
    started_at: datetime | None
    finished_at: datetime | None
    duration_sec: int | None
    exit_code: int | None

    model_config = {"from_attributes": True}


# ── Pipeline ─────────────────────────────────────────────────────────────────

class PipelineCreate(BaseModel):
    """POST /api/v1/pipelines — hem manuel hem webhook tetiklemesi için."""
    repo_url: HttpUrl
    branch: str
    commit_hash: str | None = None
    commit_msg: str | None = None
    commit_author: str | None = None
    trigger_type: TriggerType = TriggerType.manual


class PipelineListItem(BaseModel):
    """GET /api/v1/pipelines listesindeki her eleman."""
    id: str
    repo_id: str | None
    repo_url: str
    branch: str
    commit_hash: str | None
    trigger_type: TriggerType
    status: PipelineStatus
    started_at: datetime | None
    finished_at: datetime | None
    duration_sec: int | None

    model_config = {"from_attributes": True}


class PipelineDetailResponse(BaseModel):
    """GET /api/v1/pipelines/{id} — adımlar dahil tam detay."""
    id: str
    repo_id: str | None
    repo_url: str
    branch: str
    commit_hash: str | None
    commit_msg: str | None
    commit_author: str | None
    trigger_type: TriggerType
    status: PipelineStatus
    started_at: datetime | None
    finished_at: datetime | None
    duration_sec: int | None
    steps: list[StepResponse]

    model_config = {"from_attributes": True}


class PipelineCreateResponse(BaseModel):
    """POST /api/v1/pipelines yanıtı — 201 Created."""
    id: str
    status: PipelineStatus
    trigger_type: TriggerType
    branch: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PipelineReportResponse(BaseModel):
    """GET /api/v1/pipelines/{id}/report."""
    pipeline_id: str
    status: PipelineStatus
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration_sec: float
