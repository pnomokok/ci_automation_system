from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.log import LogLineResponse
from app.schemas.pipeline import (
    PipelineCreate,
    PipelineCreateResponse,
    PipelineDetailResponse,
    PipelineListItem,
    PipelineReportResponse,
)
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/pipelines", tags=["pipelines"])
_service = PipelineService()


@router.get("", response_model=PaginatedResponse[PipelineListItem])
async def list_pipelines(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    repo_id: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, total = await _service.list(session, page, page_size, status, repo_id, user=_)
    return PaginatedResponse[PipelineListItem](
        items=[PipelineListItem.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=PipelineCreateResponse, status_code=201)
async def create_pipeline(
    body: PipelineCreate,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    pipeline = await _service.create(session, redis, body, user=current_user)
    return PipelineCreateResponse.model_validate(pipeline)


@router.get("/{pipeline_id}", response_model=PipelineDetailResponse)
async def get_pipeline(
    pipeline_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pipeline = await _service.get(session, pipeline_id, user=current_user)
    return PipelineDetailResponse.model_validate(pipeline)


@router.post("/{pipeline_id}/stop")
async def stop_pipeline(
    pipeline_id: str,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    pipeline = await _service.stop(session, redis, pipeline_id, user=current_user)
    return {"pipeline_id": pipeline.id, "status": pipeline.status}


@router.get("/{pipeline_id}/logs", response_model=PaginatedResponse[LogLineResponse])
async def get_logs(
    pipeline_id: str,
    step_name: str | None = Query(None),
    stream: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows, total = await _service.get_logs(session, pipeline_id, step_name, stream, page, page_size, user=current_user)
    items = [
        LogLineResponse(
            step_id=log.step_id,
            step_name=step_name_val,
            line_number=log.line_number,
            stream=log.stream,
            timestamp=log.timestamp,
            content=log.content,
        )
        for log, step_name_val in rows
    ]
    return PaginatedResponse[LogLineResponse](items=items, total=total, page=page, page_size=page_size)


@router.get("/{pipeline_id}/report", response_model=PipelineReportResponse)
async def get_report(
    pipeline_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _service.get_report(session, pipeline_id, user=current_user)
