import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.repository_repo import RepositoryRepository
from app.repositories.team_repo import TeamRepository
from app.schemas.repository import RepositoryCreate

_repo = RepositoryRepository()
_team_repo = TeamRepository()

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
        team_id = data.owner_id if data.owner_type == 'team' else None
        repo = await _repo.create(session, {
            "url":            str(data.url),
            "default_branch": data.default_branch,
            "webhook_secret": data.webhook_secret,
            "user_id":        current_user_id,
            "team_id":        team_id,
        })
        await session.commit()
        return repo

    async def list(self, session: AsyncSession, current_user_id: str):
        teams = await _team_repo.get_all_for_user(session, current_user_id)
        team_ids = [t.id for t in teams]
        return await _repo.get_all(session, current_user_id, team_ids)

    async def delete(self, session: AsyncSession, repo_id: str):
        deleted = await _repo.delete(session, repo_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PIPELINE_NOT_FOUND", "message": "Depo bulunamadı"},
            )
        await session.commit()
