import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TriggerType(str, Enum):
    webhook = "webhook"
    manual = "manual"


class PipelineStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("repositories.id"), nullable=True)
    triggered_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    repo_url: Mapped[str] = mapped_column(String(512), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_hash: Mapped[str | None] = mapped_column(String(40), nullable=True)
    commit_msg: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    commit_author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False, default=TriggerType.manual)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=PipelineStatus.QUEUED)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    repository: Mapped["Repository | None"] = relationship("Repository", back_populates="pipelines")
    triggered_by: Mapped["User | None"] = relationship("User", foreign_keys=[triggered_by_id])
    steps: Mapped[list["Step"]] = relationship("Step", back_populates="pipeline", order_by="Step.order")
