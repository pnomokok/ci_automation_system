from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository


class RepositoryRepository:

    async def create(self, session: AsyncSession, data: dict) -> Repository:
        repo = Repository(**data)
        session.add(repo)
        await session.flush()
        await session.refresh(repo)
        return repo

    async def get_by_id(self, session: AsyncSession, repo_id: str) -> Repository | None:
        result = await session.execute(select(Repository).where(Repository.id == repo_id))
        return result.scalar_one_or_none()

    async def get_by_url(self, session: AsyncSession, url: str) -> Repository | None:
        result = await session.execute(select(Repository).where(Repository.url == url))
        return result.scalar_one_or_none()

    async def get_all(self, session: AsyncSession) -> list[Repository]:
        result = await session.execute(select(Repository).order_by(Repository.created_at.desc()))
        return list(result.scalars().all())

    async def delete(self, session: AsyncSession, repo_id: str) -> bool:
        result = await session.execute(delete(Repository).where(Repository.id == repo_id))
        await session.flush()
        return result.rowcount > 0
