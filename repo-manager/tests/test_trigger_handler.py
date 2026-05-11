import pytest
from unittest.mock import MagicMock, patch

from app.trigger_handler import (
    create_workspace,
    build_pipeline_request,
    prepare_manual_trigger_payload,
    send_to_orchestrator,
)


def test_create_workspace_uses_env_var(monkeypatch):
    monkeypatch.setenv("WORKSPACE_ROOT", "/custom/workspaces")
    with patch("app.trigger_handler.create_temp_workspace", return_value="/custom/workspaces/tmp-abc") as mock_fn:
        result = create_workspace()
    mock_fn.assert_called_once_with("/custom/workspaces")
    assert result == "/custom/workspaces/tmp-abc"


def test_create_workspace_default_root(monkeypatch):
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    with patch("app.trigger_handler.create_temp_workspace", return_value="/shared/workspaces/tmp-x") as mock_fn:
        create_workspace()
    mock_fn.assert_called_once_with("/shared/workspaces")


def test_build_pipeline_request_defaults():
    data = {
        "repo_url": "https://github.com/org/repo",
        "branch": "main",
        "commit_hash": "abc123",
        "commit_msg": "Initial commit",
        "commit_author": "Alice",
    }
    result = build_pipeline_request(data)
    assert result["trigger_type"] == "webhook"
    assert result["repo_url"] == "https://github.com/org/repo"
    assert result["workspace"] is None
    assert result["team_id"] is None


def test_build_pipeline_request_with_optional_fields():
    data = {
        "repo_url": "https://github.com/org/repo",
        "branch": "dev",
        "commit_hash": "def456",
        "commit_msg": "Feature",
        "commit_author": "Bob",
        "trigger_type": "manual",
        "workspace": "/shared/workspaces/pipe-1",
        "team_id": "team-42",
        "triggered_by_username": "bob",
    }
    result = build_pipeline_request(data)
    assert result["trigger_type"] == "manual"
    assert result["workspace"] == "/shared/workspaces/pipe-1"
    assert result["triggered_by_username"] == "bob"


def test_prepare_manual_trigger_payload(monkeypatch):
    monkeypatch.setattr("app.trigger_handler.create_workspace", lambda: "/tmp/ws/tmp-test")
    monkeypatch.setattr("app.trigger_handler.ensure_repository_state", lambda url, branch, ws: ws)
    monkeypatch.setattr("app.trigger_handler.get_latest_commit_info", lambda ws: {
        "commit_hash": "abc123",
        "commit_msg": "Test commit",
        "commit_author": "Alice",
    })

    result = prepare_manual_trigger_payload("https://github.com/org/repo", "main")

    assert result["repo_url"] == "https://github.com/org/repo"
    assert result["branch"] == "main"
    assert result["commit_hash"] == "abc123"
    assert result["commit_msg"] == "Test commit"
    assert result["workspace"] == "/tmp/ws/tmp-test"


def test_send_to_orchestrator_returns_json(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.content = b'{"id": "pipe-123", "status": "QUEUED"}'
    mock_resp.json.return_value = {"id": "pipe-123", "status": "QUEUED"}

    with patch("requests.post", return_value=mock_resp):
        result = send_to_orchestrator({"repo_url": "...", "branch": "main"})

    assert result == {"id": "pipe-123", "status": "QUEUED"}


def test_send_to_orchestrator_empty_body_returns_queued(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.content = b""

    with patch("requests.post", return_value=mock_resp):
        result = send_to_orchestrator({"repo_url": "...", "branch": "main"})

    assert result == {"status": "queued"}


def test_send_to_orchestrator_uses_env_url(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_URL", "http://my-orchestrator:9000")
    mock_resp = MagicMock()
    mock_resp.content = b"{}"
    mock_resp.json.return_value = {}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        send_to_orchestrator({"repo_url": "...", "branch": "main"})

    called_url = mock_post.call_args[0][0]
    assert "my-orchestrator:9000" in called_url
