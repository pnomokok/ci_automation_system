from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.repository import RepositoryCreate, RepositoryResponse
from app.services.repository_service import RepositoryService

router = APIRouter(prefix="/repositories", tags=["repositories"])
_service = RepositoryService()


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repos = await _service.list(session)
    return [RepositoryResponse.model_validate(r) for r in repos]


@router.post("", response_model=RepositoryResponse, status_code=201)
async def create_repository(
    body: RepositoryCreate,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = await _service.create(session, body)
    return RepositoryResponse.model_validate(repo)


@router.delete("/{repo_id}", status_code=204)
async def delete_repository(
    repo_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _service.delete(session, repo_id)
