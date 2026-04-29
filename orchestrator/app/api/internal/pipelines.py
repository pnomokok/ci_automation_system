from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.redis import get_redis
from app.schemas.internal import PipelineUpdateRequest, PipelineUpdateResponse
from app.schemas.pipeline import PipelineCreate, PipelineCreateResponse
from app.services.pipeline_service import PipelineService
from app.services.step_service import StepService

router = APIRouter(tags=["internal"])
_step_service = StepService()
_pipeline_service = PipelineService()


@router.patch("/pipelines/{pipeline_id}", response_model=PipelineUpdateResponse)
async def update_pipeline(
    pipeline_id: str,
    body: PipelineUpdateRequest,
    session: AsyncSession = Depends(get_db),
):
    result = await _step_service.update_pipeline(session, pipeline_id, body)
    return PipelineUpdateResponse(**result)


@router.post("/pipelines/trigger", response_model=PipelineCreateResponse, status_code=201)
async def trigger_pipeline(
    body: PipelineCreate,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Repo Manager tarafından çağrılır — JWT gerektirmez, yalnızca Docker ağından erişilir."""
    pipeline = await _pipeline_service.create(session, redis, body)
    return pipeline
