import os
import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class OrchestratorAPIClient:
    def __init__(self):
        self.base_url = os.environ.get("ORCHESTRATOR_API_URL", "http://orchestrator:8000")
        self.session = requests.Session()

    def update_step_status(self, step_id: str, status: str, exit_code: int | None = None) -> bool:
        """PATCH /api/v1/internal/steps/{step_id}"""
        url = f"{self.base_url}/api/v1/internal/steps/{step_id}"
        now = datetime.now(timezone.utc).isoformat()
        payload: dict = {"status": status}
        if status == "RUNNING":
            payload["started_at"] = now
        elif status in ("SUCCESS", "FAILED"):
            payload["finished_at"] = now
        if exit_code is not None:
            payload["exit_code"] = exit_code
        try:
            response = self.session.patch(url, json=payload, timeout=5)
            response.raise_for_status()
            logger.info(f"Successfully updated step {step_id} status to {status}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to update step {step_id} status: {e}")
            return False

    def send_step_logs(self, step_id: str, log_lines: list[str]) -> bool:
        """POST /api/v1/internal/steps/{step_id}/logs"""
        if not log_lines:
            return True
        url = f"{self.base_url}/api/v1/internal/steps/{step_id}/logs"
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "lines": [
                {
                    "line_number": i + 1,
                    "stream": "stdout",
                    "timestamp": now,
                    "content": line,
                }
                for i, line in enumerate(log_lines)
            ]
        }
        try:
            response = self.session.post(url, json=payload, timeout=5)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to send logs for step {step_id}: {e}")
            return False

    def update_pipeline_status(self, pipeline_id: str, status: str) -> bool:
        """PATCH /api/v1/internal/pipelines/{pipeline_id}"""
        url = f"{self.base_url}/api/v1/internal/pipelines/{pipeline_id}"
        now = datetime.now(timezone.utc).isoformat()
        payload: dict = {"status": status}
        if status in ("SUCCESS", "FAILED", "STOPPED"):
            payload["finished_at"] = now
        try:
            response = self.session.patch(url, json=payload, timeout=5)
            response.raise_for_status()
            logger.info(f"Successfully updated pipeline {pipeline_id} status to {status}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to update pipeline {pipeline_id} status: {e}")
            return False
