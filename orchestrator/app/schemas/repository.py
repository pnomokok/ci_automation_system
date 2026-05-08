from datetime import datetime

from pydantic import BaseModel, HttpUrl, model_validator


class RepositoryCreate(BaseModel):
    url: HttpUrl
    default_branch: str = 'main'
    webhook_secret: str
    owner_type: str = 'user'
    owner_id: str | None = None


class RepositoryResponse(BaseModel):
    id: str
    url: str
    default_branch: str
    created_at: datetime
    user_id: str | None = None
    team_id: str | None = None
    owner_type: str = 'user'
    owner_id: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode='after')
    def set_owner_fields(self):
        if self.team_id:
            self.owner_type = 'team'
            self.owner_id = self.team_id
        else:
            self.owner_type = 'user'
            self.owner_id = self.user_id
        return self
