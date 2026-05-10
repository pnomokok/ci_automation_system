from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.redis import get_redis
from app.models.repository_member import RepoRole
from app.models.user import User
from app.repositories.repository_member_repo import RepositoryMemberRepository
from app.repositories.repository_repo import RepositoryRepository
from app.repositories.user_repo import UserRepository
from app.schemas.repository import RepositoryCreate, RepositoryResponse, RepositoryUpdate
from app.schemas.repository_member import (
    RepositoryMemberAdd,
    RepositoryMemberResponse,
    RepositoryMemberRoleUpdate,
)
from app.services.repository_service import RepositoryService

router = APIRouter(prefix="/repositories", tags=["repositories"])
_service = RepositoryService()
_member_repo = RepositoryMemberRepository()
_repo_repo = RepositoryRepository()
_user_repo = UserRepository()


def _build_response(repo, my_role: RepoRole) -> RepositoryResponse:
    return RepositoryResponse(
        id=repo.id,
        url=repo.url,
        default_branch=repo.default_branch,
        created_at=repo.created_at,
        my_role=my_role,
    )


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repos = await _service.list(session, current_user.id)
    out: list[RepositoryResponse] = []
    for repo in repos:
        member = await _member_repo.get(session, repo.id, current_user.id)
        out.append(_build_response(repo, RepoRole(member.role)))
    return out


@router.post("", response_model=RepositoryResponse, status_code=201)
async def create_repository(
    body: RepositoryCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = await _service.create(session, body, current_user.id)
    return _build_response(repo, RepoRole.owner)


@router.patch("/{repo_id}", response_model=RepositoryResponse)
async def update_repository(
    repo_id: str,
    body: RepositoryUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = await _service.update(session, repo_id, body, current_user.id)
    await session.commit()
    member = await _member_repo.get(session, repo_id, current_user.id)
    return _build_response(repo, RepoRole(member.role))


@router.delete("/{repo_id}", status_code=204)
async def delete_repository(
    repo_id: str,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    await _service.delete(session, repo_id, current_user.id, redis)


# ── Members ──────────────────────────────────────────────────────────────────

async def _require_owner(session: AsyncSession, repo_id: str, user_id: str) -> None:
    repo = await _repo_repo.get_by_id(session, repo_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Depo bulunamadı"},
        )
    if not await _member_repo.is_owner(session, repo_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Bu işlem için owner yetkisi gerekli"},
        )


async def _require_member(session: AsyncSession, repo_id: str, user_id: str) -> None:
    repo = await _repo_repo.get_by_id(session, repo_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Depo bulunamadı"},
        )
    if not await _member_repo.is_member(session, repo_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Bu deponun üyesi değilsiniz"},
        )


@router.get("/{repo_id}/members", response_model=list[RepositoryMemberResponse])
async def list_members(
    repo_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_member(session, repo_id, current_user.id)
    rows = await _member_repo.list_for_repo(session, repo_id)
    return [
        RepositoryMemberResponse(
            id=m.id,
            user_id=m.user_id,
            username=username,
            role=RepoRole(m.role),
            created_at=m.created_at,
        )
        for m, username in rows
    ]


@router.post("/{repo_id}/members", response_model=RepositoryMemberResponse, status_code=201)
async def add_member(
    repo_id: str,
    body: RepositoryMemberAdd,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_owner(session, repo_id, current_user.id)

    user = await _user_repo.get_by_username(session, body.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Kullanıcı bulunamadı: {body.username}"},
        )
    if await _member_repo.is_member(session, repo_id, user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_MEMBER", "message": "Kullanıcı zaten bu deponun üyesi"},
        )

    member = await _member_repo.add(session, repo_id, user.id, body.role.value)
    await session.commit()
    return RepositoryMemberResponse(
        id=member.id,
        user_id=member.user_id,
        username=user.username,
        role=RepoRole(member.role),
        created_at=member.created_at,
    )


@router.patch("/{repo_id}/members/{user_id}", status_code=204)
async def update_member_role(
    repo_id: str,
    user_id: str,
    body: RepositoryMemberRoleUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_owner(session, repo_id, current_user.id)

    if user_id == current_user.id and body.role != RepoRole.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "Kendinizi member'a düşüremezsiniz"},
        )

    target = await _member_repo.get(session, repo_id, user_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Bu kullanıcı deponun üyesi değil"},
        )

    # Owner'ı member'a düşürme: son owner ise reddet
    if target.role == RepoRole.owner.value and body.role == RepoRole.member:
        owner_count = await _member_repo.count_owners(session, repo_id)
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "LAST_OWNER", "message": "Son owner indirilemez. Önce başka bir owner atayın."},
            )

    await _member_repo.update_role(session, repo_id, user_id, body.role.value)
    await session.commit()


@router.delete("/{repo_id}/members/{user_id}", status_code=204)
async def remove_member(
    repo_id: str,
    user_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_owner(session, repo_id, current_user.id)

    target = await _member_repo.get(session, repo_id, user_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Bu kullanıcı deponun üyesi değil"},
        )

    # Son owner çıkarılamaz
    if target.role == RepoRole.owner.value:
        owner_count = await _member_repo.count_owners(session, repo_id)
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "LAST_OWNER", "message": "Son owner çıkarılamaz. Önce başka bir owner atayın."},
            )

    await _member_repo.remove(session, repo_id, user_id)
    await session.commit()
