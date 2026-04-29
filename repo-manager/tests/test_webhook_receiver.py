from fastapi.testclient import TestClient

from app.signature_validator import build_signature
from app.webhook_receiver import app

client = TestClient(app)


def test_webhook_accepts_valid_push(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "secret")
    monkeypatch.setenv("WORKSPACE_ROOT", "/tmp/workspaces")
    body = b'{"ref":"refs/heads/main","after":"abc123456789","repository":{"name":"sample-repo","clone_url":"https://github.com/org/sample-repo.git"},"head_commit":{"id":"abc123456789","message":"Initial commit","timestamp":"2026-04-28T10:00:00Z","author":{"name":"Zeynep"}}}'
    signature = build_signature("secret", body)

    monkeypatch.setattr("app.API.webhook.create_workspace", lambda: "/tmp/workspaces/tmp-test")
    monkeypatch.setattr("app.API.webhook.ensure_repository_state", lambda url, branch, ws: ws)
    monkeypatch.setattr("app.API.webhook.checkout_commit", lambda ws, commit: None)
    monkeypatch.setattr("app.API.webhook.load_allowed_branches", lambda repo_path: ["main"])
    monkeypatch.setattr(
        "app.API.webhook.send_to_orchestrator",
        lambda payload: {"id": "pipe-456", "status": "QUEUED", "branch": payload["branch"]},
    )

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": signature,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert response.json()["orchestrator"]["id"] == "pipe-456"


def test_webhook_rejects_invalid_signature(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "secret")
    response = client.post(
        "/webhook",
        content=b"{}",
        headers={
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": "sha256=invalid",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 401
