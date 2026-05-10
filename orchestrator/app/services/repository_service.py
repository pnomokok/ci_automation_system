import httpx
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository_member import RepoRole
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.repository_member_repo import RepositoryMemberRepository
from app.repositories.repository_repo import RepositoryRepository
from app.schemas.repository import RepositoryCreate, RepositoryUpdate

_repo = RepositoryRepository()
_member_repo = RepositoryMemberRepository()
_pipeline_repo = PipelineRepository()

_GITHUB_PREFIX = "https://github.com/"


async def _assert_public_github_repo(url: str) -> None:
    """Raises 400 if the URL is not an accessible public GitHub repository."""
    if not url.startswith(_GITHUB_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "Yalnızca GitHub repoları desteklenmektedir (https://github.com/...)"},
        )

    path = url.removeprefix(_GITHUB_PREFIX).rstrip("/")
    parts = path.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "Geçerli bir GitHub repo URL'i girin (https://github.com/kullanici/repo)"},
        )

    owner, repo = parts[0], parts[1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(api_url, headers={"Accept": "application/vnd.github+json"})
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "GitHub'a ulaşılamadı. Lütfen URL'i kontrol edin."},
        )

    if resp.status_code == 200:
        if resp.json().get("private", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_INPUT", "message": "Private repolar eklenemez. Yalnızca public GitHub repoları desteklenmektedir."},
            )
    elif resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "Repo bulunamadı veya private. Yalnızca public GitHub repoları eklenebilir."},
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": f"GitHub'dan beklenmedik yanıt alındı (HTTP {resp.status_code})."},
        )


class RepositoryService:

    async def create(self, session: AsyncSession, data: RepositoryCreate, current_user_id: str):
        await _assert_public_github_repo(str(data.url))

        existing = await _repo.get_by_url(session, str(data.url))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "ALREADY_RUNNING", "message": "Bu URL zaten kayıtlı"},
            )
        repo = await _repo.create(session, {
            "url":            str(data.url),
            "default_branch": data.default_branch,
            "webhook_secret": data.webhook_secret,
        })
        await _member_repo.add(session, repo.id, current_user_id, RepoRole.owner.value)
        await session.commit()
        return repo

    async def update(self, session: AsyncSession, repo_id: str, data: RepositoryUpdate, current_user_id: str):
        repo = await _repo.get_by_id(session, repo_id)
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "Depo bulunamadı"},
            )
        if not await _member_repo.is_owner(session, repo_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Bu işlem için owner yetkisi gerekli"},
            )
        patch = {k: v for k, v in data.model_dump().items() if v is not None}
        if not patch:
            return repo
        return await _repo.update(session, repo_id, patch)

    async def list(self, session: AsyncSession, current_user_id: str):
        return await _repo.list_for_user(session, current_user_id)

    async def delete(self, session: AsyncSession, repo_id: str, current_user_id: str, redis: Redis):
        repo = await _repo.get_by_id(session, repo_id)
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "Depo bulunamadı"},
            )
        if not await _member_repo.is_owner(session, repo_id, current_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Bu depoyu silme yetkiniz yok (yalnızca owner silebilir)"},
            )

        # Aktif pipeline'lar için runner'a stop sinyali gönder
        active = await _pipeline_repo.list_active_for_repo(session, repo_id)
        for p in active:
            await redis.set(f"pipeline_stop:{p.id}", "1", ex=3600)

        # Bu repoya ait tüm pipeline'ları sil (steps + logs cascade ile temizlenir)
        pipeline_ids = await _pipeline_repo.list_ids_for_repo(session, repo_id)
        for pid in pipeline_ids:
            await _pipeline_repo.delete(session, pid)

        # Repository'yi sil (üyelikler FK CASCADE ile temizlenir)
        await _repo.delete(session, repo_id)
        await session.commit()
