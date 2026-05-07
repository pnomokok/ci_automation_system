from datetime import datetime
from pydantic import BaseModel


class TeamCreate(BaseModel):
    name: str


class TeamResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamMemberAdd(BaseModel):
    username: str


class TeamMemberResponse(BaseModel):
    user_id: str
    username: str
    joined_at: datetime
