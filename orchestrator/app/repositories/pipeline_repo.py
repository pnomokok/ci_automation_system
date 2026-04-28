from datetime import datetime, timezone

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pipeline import Pipeline, PipelineStatus


class PipelineRepository:

    async def create(self, session: AsyncSession, data: dict) -> Pipeline:
        pipeline = Pipeline(**data)
        session.add(pipeline)
        await session.flush()
        await session.refresh(pipeline)
        return pipeline

    async def get_by_id(self, session: AsyncSession, pipeline_id: str) -> Pipeline | None:
        result = await session.execute(
            select(Pipeline)
            .options(selectinload(Pipeline.steps))
            .where(Pipeline.id == pipeline_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        session: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        repo_id: str | None = None,
    ) -> tuple[list[Pipeline], int]:
        query = select(Pipeline)
        if status:
            query = query.where(Pipeline.status == status)
        if repo_id:
            query = query.where(Pipeline.repo_id == repo_id)

        total_result = await session.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        query = query.order_by(Pipeline.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        return list(result.scalars().all()), total

    async def update_status(
        self,
        session: AsyncSession,
        pipeline_id: str,
        status: PipelineStatus,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        duration_sec: int | None = None,
    ) -> Pipeline | None:
        values: dict = {"status": status}
        if started_at is not None:
            values["started_at"] = started_at
        if finished_at is not None:
            values["finished_at"] = finished_at
        if duration_sec is not None:
            values["duration_sec"] = duration_sec

        await session.execute(
            update(Pipeline).where(Pipeline.id == pipeline_id).values(**values)
        )
        await session.flush()
        return await self.get_by_id(session, pipeline_id)

    async def count_running(self, session: AsyncSession) -> int:
        result = await session.execute(
            select(func.count()).where(Pipeline.status == PipelineStatus.RUNNING)
        )
        return result.scalar_one()
