import os
from typing import Any

import requests

from app.git_client import create_temp_workspace, ensure_repository_state, get_latest_commit_info


def create_workspace() -> str:
    return create_temp_workspace(os.getenv("WORKSPACE_ROOT", "/shared/workspaces"))


def build_pipeline_request(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo_url": data["repo_url"],
        "branch": data["branch"],
        "commit_hash": data["commit_hash"],
        "commit_msg": data["commit_msg"],
        "commit_author": data["commit_author"],
        "trigger_type": data.get("trigger_type", "webhook"),
        "workspace": data.get("workspace"),
        "team_id": data.get("team_id"),
        "triggered_by_username": data.get("triggered_by_username"),
    }


def prepare_manual_trigger_payload(repo_url: str, branch: str) -> dict[str, Any]:
    workspace = create_workspace()
    ensure_repository_state(repo_url, branch, workspace)
    commit_info = get_latest_commit_info(workspace)
    return {
        "repo_url": repo_url,
        "branch": branch,
        "commit_hash": commit_info["commit_hash"],
        "commit_msg": commit_info["commit_msg"],
        "commit_author": commit_info["commit_author"],
        "workspace": workspace,
    }


def send_to_orchestrator(payload: dict[str, Any]) -> dict[str, Any]:
    orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
    response = requests.post(
        f"{orchestrator_url}/api/v1/internal/pipelines/trigger",
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    return response.json() if response.content else {"status": "queued"}
