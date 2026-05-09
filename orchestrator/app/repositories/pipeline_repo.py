from datetime import datetime

from sqlalchemy import select, func, update, or_, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.log import Log
from app.models.pipeline import Pipeline, PipelineStatus
from app.models.repository_member import RepositoryMember
from app.models.step import Step


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
            .options(selectinload(Pipeline.steps), selectinload(Pipeline.triggered_by))
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
        user_id: str | None = None,
    ) -> tuple[list[Pipeline], int]:
        query = select(Pipeline).options(selectinload(Pipeline.triggered_by))
        if status:
            query = query.where(Pipeline.status == status)
        if repo_id:
            query = query.where(Pipeline.repo_id == repo_id)
        if user_id:
            user_repos = select(RepositoryMember.repo_id).where(RepositoryMember.user_id == user_id)
            query = query.where(
                or_(
                    Pipeline.repo_id.is_(None),
                    Pipeline.repo_id.in_(user_repos),
                )
            )

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

    async def delete(self, session: AsyncSession, pipeline_id: str) -> None:
        step_result = await session.execute(
            select(Step.id).where(Step.pipeline_id == pipeline_id)
        )
        step_ids = list(step_result.scalars().all())
        if step_ids:
            await session.execute(sql_delete(Log).where(Log.step_id.in_(step_ids)))
            await session.execute(sql_delete(Step).where(Step.pipeline_id == pipeline_id))
        await session.execute(sql_delete(Pipeline).where(Pipeline.id == pipeline_id))
        await session.flush()

    async def list_active_for_repo(self, session: AsyncSession, repo_id: str) -> list[Pipeline]:
        result = await session.execute(
            select(Pipeline).where(
                Pipeline.repo_id == repo_id,
                Pipeline.status.in_([PipelineStatus.QUEUED, PipelineStatus.RUNNING]),
            )
        )
        return list(result.scalars().all())

    async def list_ids_for_repo(self, session: AsyncSession, repo_id: str) -> list[str]:
        result = await session.execute(
            select(Pipeline.id).where(Pipeline.repo_id == repo_id)
        )
        return list(result.scalars().all())

    async def get_active_by_repo_branch(
        self, session: AsyncSession, repo_url: str, branch: str
    ) -> Pipeline | None:
        result = await session.execute(
            select(Pipeline).where(
                Pipeline.repo_url == repo_url,
                Pipeline.branch == branch,
                Pipeline.status.in_([PipelineStatus.QUEUED, PipelineStatus.RUNNING]),
            )
        )
        return result.scalar_one_or_none()
