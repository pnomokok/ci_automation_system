from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.internal import (
    LogBatchRequest,
    LogBatchResponse,
    StepUpdateRequest,
    StepUpdateResponse,
)
from app.services.step_service import StepService

router = APIRouter(tags=["internal"])
_service = StepService()


@router.patch("/steps/{step_id}", response_model=StepUpdateResponse)
async def update_step(
    step_id: str,
    body: StepUpdateRequest,
    session: AsyncSession = Depends(get_db),
):
    result = await _service.update_step(session, step_id, body)
    return StepUpdateResponse(**result)


@router.post("/steps/{step_id}/logs", response_model=LogBatchResponse, status_code=201)
async def add_logs(
    step_id: str,
    body: LogBatchRequest,
    session: AsyncSession = Depends(get_db),
):
    result = await _service.add_logs(session, step_id, body)
    return LogBatchResponse(**result)
