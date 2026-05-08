from sqlalchemy import select, delete, or_
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

    async def get_all(self, session: AsyncSession, user_id: str, team_ids: list[str]) -> list[Repository]:
        conditions = [
            Repository.user_id == user_id,
            Repository.user_id.is_(None),  # migration öncesi eklenen repolar herkese görünür
        ]
        if team_ids:
            conditions.append(Repository.team_id.in_(team_ids))
        stmt = select(Repository).where(or_(*conditions)).order_by(Repository.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, session: AsyncSession, repo_id: str) -> bool:
        result = await session.execute(delete(Repository).where(Repository.id == repo_id))
        await session.flush()
        return result.rowcount > 0
