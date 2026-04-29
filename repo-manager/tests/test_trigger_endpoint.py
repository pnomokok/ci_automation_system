from fastapi.testclient import TestClient

from app.git_client import GitOperationError
from app.webhook_receiver import app

client = TestClient(app)


def test_trigger_returns_contract_fields(monkeypatch) -> None:
    def fake_prepare(repo_url: str, branch: str) -> dict[str, str]:
        return {
            "repo_url": repo_url,
            "branch": branch,
            "commit_hash": "abc123456789",
            "commit_msg": "Manual trigger",
            "commit_author": "Zeynep",
            "workspace": "/shared/workspaces/tmp-abc123",
        }

    monkeypatch.setattr(
        "app.API.trigger.prepare_manual_trigger_payload",
        fake_prepare,
    )

    response = client.post(
        "/trigger",
        json={
            "repo_url": "https://github.com/org/sample-repo.git",
            "branch": "main",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "repo_url": "https://github.com/org/sample-repo.git",
        "branch": "main",
        "commit_hash": "abc123456789",
        "commit_msg": "Manual trigger",
        "commit_author": "Zeynep",
        "workspace": "/shared/workspaces/tmp-abc123",
    }


def test_trigger_returns_500_when_repository_preparation_fails(monkeypatch) -> None:
    def fake_prepare(repo_url: str, branch: str) -> dict[str, str]:
        raise GitOperationError("clone", "authentication failed")

    monkeypatch.setattr(
        "app.API.trigger.prepare_manual_trigger_payload",
        fake_prepare,
    )

    response = client.post(
        "/trigger",
        json={
            "repo_url": "https://github.com/org/sample-repo.git",
            "branch": "main",
        },
    )

    assert response.status_code == 500
    assert "Repository preparation failed" in response.json()["detail"]
