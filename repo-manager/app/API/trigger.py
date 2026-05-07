import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from requests import HTTPError, RequestException

from app.git_client import GitOperationError
from app.trigger_handler import build_pipeline_request, prepare_manual_trigger_payload, send_to_orchestrator

router = APIRouter(tags=["trigger"])

_api_key_header = APIKeyHeader(name="X-Trigger-Token", auto_error=False)


def _verify_trigger_token(token: str | None = Security(_api_key_header)) -> None:
    expected = os.getenv("TRIGGER_API_KEY", "")
    if not expected:
        return  # Token yapılandırılmamışsa (geliştirme ortamı) geçer
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid trigger token")


class TriggerRequest(BaseModel):
    repo_url: str
    branch: str
    team_id: str | None = None


@router.post("/trigger")
async def trigger_pipeline(
    payload: TriggerRequest,
    _: None = Depends(_verify_trigger_token),
) -> dict[str, Any]:
    try:
        data = prepare_manual_trigger_payload(payload.repo_url, payload.branch)
        data["trigger_type"] = "manual"
        data["team_id"] = payload.team_id
        pipeline_request = build_pipeline_request(data)
        return send_to_orchestrator(pipeline_request)
    except GitOperationError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Repository preparation failed: {exc}",
        ) from exc
    except HTTPError as exc:
        # Orchestrator'dan gelen 4xx hataları (ör. 409 ALREADY_RUNNING) olduğu gibi ilet
        status_code = exc.response.status_code if exc.response is not None else 502
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach orchestrator: {exc}",
        ) from exc
