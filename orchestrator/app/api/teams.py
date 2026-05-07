from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.team import TeamCreate, TeamResponse, TeamMemberAdd, TeamMemberResponse
from app.services.team_service import TeamService

router = APIRouter(prefix="/teams", tags=["teams"])
_service = TeamService()


@router.post("", response_model=TeamResponse, status_code=201)
async def create_team(
    body: TeamCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = await _service.create(session, body, creator=current_user)
    return TeamResponse.model_validate(team)


@router.get("", response_model=list[TeamResponse])
async def list_teams(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teams = await _service.list_for_user(session, current_user)
    return [TeamResponse.model_validate(t) for t in teams]


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = await _service.get(session, team_id, current_user)
    return TeamResponse.model_validate(team)


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
async def list_members(
    team_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    members = await _service.list_members(session, team_id, current_user)
    return [TeamMemberResponse(**m) for m in members]


@router.post("/{team_id}/members", status_code=201)
async def add_member(
    team_id: str,
    body: TeamMemberAdd,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _service.add_member(session, team_id, body.username, requester=current_user)


@router.delete("/{team_id}/members/{user_id}", status_code=204)
async def remove_member(
    team_id: str,
    user_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _service.remove_member(session, team_id, user_id, requester=current_user)
