import logging
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from requests import RequestException

logger = logging.getLogger(__name__)

from app.branch_filter import is_branch_allowed, load_allowed_branches
from app.commit_parser import parse_push_payload
from app.git_client import checkout_commit, ensure_repository_state
from app.signature_validator import is_valid_signature
from app.trigger_handler import build_pipeline_request, create_workspace, send_to_orchestrator

router = APIRouter(tags=["webhook"])


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    x_github_event: str = Header(default="", alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(default="", alias="X-Hub-Signature-256"),
) -> dict[str, Any]:
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    raw_body = await request.body()

    if not is_valid_signature(secret, raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    if x_github_event != "push":
        raise HTTPException(status_code=400, detail="Only push events are supported")

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    parsed_payload = parse_push_payload(payload)

    if not parsed_payload["branch"]:
        raise HTTPException(status_code=400, detail="Missing branch information")

    workspace = create_workspace()
    ensure_repository_state(parsed_payload["repo_url"], parsed_payload["branch"], workspace)
    checkout_commit(workspace, parsed_payload["commit_hash"])

    allowed_branches = load_allowed_branches(workspace)
    if not is_branch_allowed(parsed_payload["branch"], allowed_branches):
        logger.info(
            "Branch '%s' is not in the allowed list %s — webhook ignored",
            parsed_payload["branch"],
            allowed_branches,
        )
        return {"status": "ignored"}

    parsed_payload["workspace"] = workspace
    pipeline_request = build_pipeline_request(parsed_payload)
    try:
        orchestrator_response = send_to_orchestrator(pipeline_request)
        return {
            "status": "queued",
            "orchestrator": orchestrator_response,
        }
    except RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach orchestrator: {exc}",
        ) from exc
