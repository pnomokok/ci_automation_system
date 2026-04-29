from datetime import datetime

from pydantic import BaseModel, HttpUrl


class RepositoryCreate(BaseModel):
    url: HttpUrl
    default_branch: str
    webhook_secret: str


class RepositoryResponse(BaseModel):
    id: str
    url: str
    default_branch: str
    created_at: datetime

    model_config = {"from_attributes": True}
