from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log import Log
from app.models.step import Step


class LogRepository:

    async def create_many(self, session: AsyncSession, logs_data: list[dict]) -> int:
        logs = [Log(**data) for data in logs_data]
        session.add_all(logs)
        await session.flush()
        return len(logs)

    async def get_by_pipeline_id(
        self,
        session: AsyncSession,
        pipeline_id: str,
        step_name: str | None = None,
        stream: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[tuple[Log, str]], int]:
        """Her log satırını step adıyla birlikte döner: (Log, step_name)."""
        query = (
            select(Log, Step.name.label("step_name"))
            .join(Step, Log.step_id == Step.id)
            .where(Step.pipeline_id == pipeline_id)
        )
        if step_name:
            query = query.where(Step.name == step_name)
        if stream:
            query = query.where(Log.stream == stream)

        total_result = await session.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        query = query.order_by(Log.step_id, Log.line_number)
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        return list(result.all()), total
