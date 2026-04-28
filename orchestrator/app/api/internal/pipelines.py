from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.internal import PipelineUpdateRequest, PipelineUpdateResponse
from app.services.step_service import StepService

router = APIRouter(tags=["internal"])
_service = StepService()


@router.patch("/pipelines/{pipeline_id}", response_model=PipelineUpdateResponse)
async def update_pipeline(
    pipeline_id: str,
    body: PipelineUpdateRequest,
    session: AsyncSession = Depends(get_db),
):
    result = await _service.update_pipeline(session, pipeline_id, body)
    return PipelineUpdateResponse(**result)
