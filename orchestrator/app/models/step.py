import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StepName(str, Enum):
    install = "install"
    build = "build"
    test = "test"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(16), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=StepStatus.PENDING)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="steps")
    logs: Mapped[list["Log"]] = relationship("Log", back_populates="step")
