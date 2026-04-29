from datetime import datetime, timezone

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

        now = datetime.now(timezone.utc)
        values: dict = {"status": data.status}

        started_at = data.started_at or (now if data.status == StepStatus.RUNNING else None)
        finished_at = data.finished_at or (now if data.status in (StepStatus.SUCCESS, StepStatus.FAILED) else None)

        if started_at is not None:
            values["started_at"] = started_at
        if data.exit_code is not None:
            values["exit_code"] = data.exit_code
        if finished_at is not None:
            values["finished_at"] = finished_at
            effective_start = started_at or step.started_at
            if effective_start:
                s = effective_start if effective_start.tzinfo else effective_start.replace(tzinfo=timezone.utc)
                f = finished_at if finished_at.tzinfo else finished_at.replace(tzinfo=timezone.utc)
                values["duration_sec"] = int((f - s).total_seconds())

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

        now = datetime.now(timezone.utc)
        started_at = now if data.status == PipelineStatus.RUNNING else None
        finished_at = data.finished_at or (now if data.status in (PipelineStatus.SUCCESS, PipelineStatus.FAILED, PipelineStatus.STOPPED) else None)

        duration_sec = None
        if finished_at:
            effective_start = pipeline.started_at or started_at
            if effective_start:
                s = effective_start if effective_start.tzinfo else effective_start.replace(tzinfo=timezone.utc)
                f = finished_at if finished_at.tzinfo else finished_at.replace(tzinfo=timezone.utc)
                duration_sec = int((f - s).total_seconds())

        updated = await _pipeline_repo.update_status(
            session,
            pipeline_id,
            data.status,
            started_at=started_at,
            finished_at=finished_at,
            duration_sec=duration_sec,
        )
        await session.commit()
        return {"pipeline_id": updated.id, "status": updated.status}
