from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.repository_repo import RepositoryRepository
from app.schemas.repository import RepositoryCreate

_repo = RepositoryRepository()


class RepositoryService:

    async def create(self, session: AsyncSession, data: RepositoryCreate):
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
        await session.commit()
        return repo

    async def list(self, session: AsyncSession):
        return await _repo.get_all(session)

    async def delete(self, session: AsyncSession, repo_id: str):
        deleted = await _repo.delete(session, repo_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PIPELINE_NOT_FOUND", "message": "Depo bulunamadı"},
            )
        await session.commit()
