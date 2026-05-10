from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository
from app.models.repository_member import RepositoryMember


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

    async def list_for_user(self, session: AsyncSession, user_id: str) -> list[Repository]:
        stmt = (
            select(Repository)
            .join(RepositoryMember, RepositoryMember.repo_id == Repository.id)
            .where(RepositoryMember.user_id == user_id)
            .order_by(Repository.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, session: AsyncSession, repo_id: str, data: dict) -> Repository | None:
        await session.execute(
            update(Repository).where(Repository.id == repo_id).values(**data)
        )
        await session.flush()
        return await self.get_by_id(session, repo_id)

    async def delete(self, session: AsyncSession, repo_id: str) -> bool:
        result = await session.execute(delete(Repository).where(Repository.id == repo_id))
        await session.flush()
        return result.rowcount > 0
