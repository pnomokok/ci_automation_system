from datetime import datetime

from pydantic import BaseModel

from app.models.log import StreamType


class LogLineResponse(BaseModel):
    """GET /api/v1/pipelines/{id}/logs listesindeki her satır."""
    step_id: str
    step_name: str
    line_number: int
    stream: StreamType
    timestamp: datetime
    content: str

    model_config = {"from_attributes": True}
