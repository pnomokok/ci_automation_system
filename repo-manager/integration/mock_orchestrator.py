from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel


class PipelineRequest(BaseModel):
    repo_url: str
    branch: str
    commit_hash: str
    commit_msg: str
    commit_author: str
    trigger_type: str


app = FastAPI(title="Mock Orchestrator", version="1.0.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/pipelines")
async def create_pipeline(payload: PipelineRequest) -> dict[str, Any]:
    return {
        "id": "mock-pipeline-001",
        "status": "QUEUED",
        "trigger_type": payload.trigger_type,
        "branch": payload.branch,
        "created_at": "2026-04-28T10:00:00Z",
    }
