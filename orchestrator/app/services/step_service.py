from datetime import timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline import PipelineStatus
from app.models.step import StepStatus
from app.repositories.log_repo import LogRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.step_repo import StepRepository
from app.schemas.internal import LogBatchRequest, PipelineUpdateRequest, StepUpdateRequest

_step_repo     = StepRepository()
_pipeline_repo = PipelineRepository()
_log_repo      = LogRepository()


class StepService:

    async def update_step(
        self, session: AsyncSession, step_id: str, data: StepUpdateRequest
    ) -> dict:
        step = await _step_repo.get_by_id(session, step_id)
        if step is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PIPELINE_NOT_FOUND", "message": "Step bulunamadı"},
            )

        values: dict = {"status": data.status}
        if data.started_at is not None:
            values["started_at"] = data.started_at
        if data.exit_code is not None:
            values["exit_code"] = data.exit_code
        if data.finished_at is not None:
            values["finished_at"] = data.finished_at
            if step.started_at:
                started = step.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                finished = data.finished_at
                if finished.tzinfo is None:
                    finished = finished.replace(tzinfo=timezone.utc)
                values["duration_sec"] = int((finished - started).total_seconds())

        updated = await _step_repo.update(session, step_id, values)
        await session.commit()
        return {"step_id": updated.id, "status": updated.status}

    async def add_logs(
        self, session: AsyncSession, step_id: str, data: LogBatchRequest
    ) -> dict:
        step = await _step_repo.get_by_id(session, step_id)
        if step is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PIPELINE_NOT_FOUND", "message": "Step bulunamadı"},
            )

        logs_data = [
            {
                "step_id":     step_id,
                "line_number": line.line_number,
                "stream":      line.stream,
                "timestamp":   line.timestamp,
                "content":     line.content,
            }
            for line in data.lines
        ]
        saved = await _log_repo.create_many(session, logs_data)
        await session.commit()
        return {"saved": saved}

    async def update_pipeline(
        self, session: AsyncSession, pipeline_id: str, data: PipelineUpdateRequest
    ) -> dict:
        pipeline = await _pipeline_repo.get_by_id(session, pipeline_id)
        if pipeline is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PIPELINE_NOT_FOUND", "message": "Pipeline bulunamadı"},
            )

        duration_sec = None
        if data.finished_at and pipeline.started_at:
            started = pipeline.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            finished = data.finished_at
            if finished.tzinfo is None:
                finished = finished.replace(tzinfo=timezone.utc)
            duration_sec = int((finished - started).total_seconds())

        updated = await _pipeline_repo.update_status(
            session,
            pipeline_id,
            data.status,
            finished_at=data.finished_at,
            duration_sec=duration_sec,
        )
        await session.commit()
        return {"pipeline_id": updated.id, "status": updated.status}
