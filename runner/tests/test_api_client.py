from unittest.mock import MagicMock, patch

import pytest

from app.api_client import OrchestratorAPIClient


@pytest.fixture
def client():
    return OrchestratorAPIClient()


def _mock_response(status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


# ── update_step_status ─────────────────────────────────────────────────────

def test_update_step_status_running_sends_started_at(client):
    with patch.object(client.session, "patch", return_value=_mock_response()) as mock_patch:
        client.update_step_status("step-1", "RUNNING")
        payload = mock_patch.call_args.kwargs["json"]
        assert payload["status"] == "RUNNING"
        assert "started_at" in payload
        assert "finished_at" not in payload


def test_update_step_status_success_sends_finished_at(client):
    with patch.object(client.session, "patch", return_value=_mock_response()) as mock_patch:
        client.update_step_status("step-1", "SUCCESS", exit_code=0)
        payload = mock_patch.call_args.kwargs["json"]
        assert payload["status"] == "SUCCESS"
        assert payload["exit_code"] == 0
        assert "finished_at" in payload


def test_update_step_status_returns_false_on_error(client):
    with patch.object(client.session, "patch", side_effect=Exception("network error")):
        result = client.update_step_status("step-1", "RUNNING")
        assert result is False


# ── send_step_logs ─────────────────────────────────────────────────────────

def test_send_step_logs_formats_lines_correctly(client):
    with patch.object(client.session, "post", return_value=_mock_response(201)) as mock_post:
        client.send_step_logs("step-1", ["line one", "line two"])
        payload = mock_post.call_args.kwargs["json"]
        assert len(payload["lines"]) == 2
        assert payload["lines"][0]["line_number"] == 1
        assert payload["lines"][0]["content"] == "line one"
        assert payload["lines"][1]["line_number"] == 2


def test_send_step_logs_empty_list_returns_true(client):
    with patch.object(client.session, "post") as mock_post:
        result = client.send_step_logs("step-1", [])
        mock_post.assert_not_called()
        assert result is True


def test_send_step_logs_returns_false_on_error(client):
    with patch.object(client.session, "post", side_effect=Exception("timeout")):
        result = client.send_step_logs("step-1", ["some log"])
        assert result is False


# ── update_pipeline_status ─────────────────────────────────────────────────

def test_update_pipeline_status_success_includes_finished_at(client):
    with patch.object(client.session, "patch", return_value=_mock_response()) as mock_patch:
        client.update_pipeline_status("pipe-1", "SUCCESS")
        payload = mock_patch.call_args.kwargs["json"]
        assert payload["status"] == "SUCCESS"
        assert "finished_at" in payload


def test_update_pipeline_status_running_no_finished_at(client):
    with patch.object(client.session, "patch", return_value=_mock_response()) as mock_patch:
        client.update_pipeline_status("pipe-1", "RUNNING")
        payload = mock_patch.call_args.kwargs["json"]
        assert "finished_at" not in payload
