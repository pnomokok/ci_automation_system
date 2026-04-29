from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.step import Step


class StepRepository:

    async def create_many(self, session: AsyncSession, steps_data: list[dict]) -> list[Step]:
        steps = [Step(**data) for data in steps_data]
        session.add_all(steps)
        await session.flush()
        for step in steps:
            await session.refresh(step)
        return steps

    async def get_by_id(self, session: AsyncSession, step_id: str) -> Step | None:
        result = await session.execute(select(Step).where(Step.id == step_id))
        return result.scalar_one_or_none()

    async def get_by_pipeline_id(self, session: AsyncSession, pipeline_id: str) -> list[Step]:
        result = await session.execute(
            select(Step).where(Step.pipeline_id == pipeline_id).order_by(Step.order)
        )
        return list(result.scalars().all())

    async def update(self, session: AsyncSession, step_id: str, values: dict) -> Step | None:
        await session.execute(update(Step).where(Step.id == step_id).values(**values))
        await session.flush()
        return await self.get_by_id(session, step_id)
