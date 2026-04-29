from datetime import datetime

from pydantic import BaseModel

from app.models.pipeline import PipelineStatus
from app.models.step import StepStatus
from app.models.log import StreamType


# ── Runner → Orchestrator: adım durumu ───────────────────────────────────────

class StepUpdateRequest(BaseModel):
    """PATCH /api/v1/internal/steps/{step_id}"""
    status: StepStatus
    exit_code: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class StepUpdateResponse(BaseModel):
    step_id: str
    status: StepStatus


# ── Runner → Orchestrator: log satırları ─────────────────────────────────────

class LogLine(BaseModel):
    line_number: int
    stream: StreamType
    timestamp: datetime
    content: str


class LogBatchRequest(BaseModel):
    """POST /api/v1/internal/steps/{step_id}/logs"""
    lines: list[LogLine]


class LogBatchResponse(BaseModel):
    saved: int


# ── Runner → Orchestrator: pipeline durumu ────────────────────────────────────

class PipelineUpdateRequest(BaseModel):
    """PATCH /api/v1/internal/pipelines/{pipeline_id}"""
    status: PipelineStatus
    finished_at: datetime | None = None


class PipelineUpdateResponse(BaseModel):
    pipeline_id: str
    status: PipelineStatus
