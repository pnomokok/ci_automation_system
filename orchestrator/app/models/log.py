import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StreamType(str, Enum):
    stdout = "stdout"
    stderr = "stderr"


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    step_id: Mapped[str] = mapped_column(String(36), ForeignKey("steps.id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stream: Mapped[str] = mapped_column(String(8), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    content: Mapped[str] = mapped_column(Text, nullable=False)

    step: Mapped["Step"] = relationship("Step", back_populates="logs")
