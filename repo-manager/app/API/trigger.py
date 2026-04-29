from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from requests import RequestException

from app.git_client import GitOperationError
from app.trigger_handler import build_pipeline_request, prepare_manual_trigger_payload, send_to_orchestrator

router = APIRouter(tags=["trigger"])


class TriggerRequest(BaseModel):
    repo_url: str
    branch: str


@router.post("/trigger")
async def trigger_pipeline(payload: TriggerRequest) -> dict[str, Any]:
    try:
        data = prepare_manual_trigger_payload(payload.repo_url, payload.branch)
        data["trigger_type"] = "manual"
        pipeline_request = build_pipeline_request(data)
        return send_to_orchestrator(pipeline_request)
    except GitOperationError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Repository preparation failed: {exc}",
        ) from exc
    except RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach orchestrator: {exc}",
        ) from exc
