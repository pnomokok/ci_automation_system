import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta


BASE = "/api/v1/internal"


# ── Fixture: pipeline + step'leri hazırla ─────────────────────────────────────

@pytest_asyncio.fixture
async def pipeline_with_steps(app_client):
    resp = await app_client.post("/api/v1/pipelines", json={
        "repo_url": "https://github.com/org/repo",
        "branch": "main",
    })
    data = resp.json()
    pipeline_id = data["id"]

    detail = await app_client.get(f"/api/v1/pipelines/{pipeline_id}")
    steps = detail.json()["steps"]  # [install, build, test]
    return pipeline_id, steps


# ── Step durumu güncelleme ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_step_update_to_running(app_client, pipeline_with_steps):
    pipeline_id, steps = pipeline_with_steps
    install_id = steps[0]["id"]
    now = datetime.now(timezone.utc).isoformat()

    resp = await app_client.patch(f"{BASE}/steps/{install_id}", json={
        "status": "RUNNING",
        "started_at": now,
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "RUNNING"
    assert resp.json()["step_id"] == install_id


@pytest.mark.asyncio
async def test_step_update_to_success(app_client, pipeline_with_steps):
    _, steps = pipeline_with_steps
    install_id = steps[0]["id"]
    start = datetime.now(timezone.utc)
    finish = start + timedelta(seconds=30)

    await app_client.patch(f"{BASE}/steps/{install_id}", json={
        "status": "RUNNING",
        "started_at": start.isoformat(),
    })
    resp = await app_client.patch(f"{BASE}/steps/{install_id}", json={
        "status": "SUCCESS",
        "exit_code": 0,
        "finished_at": finish.isoformat(),
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_step_update_to_failed(app_client, pipeline_with_steps):
    _, steps = pipeline_with_steps
    build_id = steps[1]["id"]

    resp = await app_client.patch(f"{BASE}/steps/{build_id}", json={
        "status": "FAILED",
        "exit_code": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "FAILED"


@pytest.mark.asyncio
async def test_step_update_nonexistent(app_client):
    resp = await app_client.patch(f"{BASE}/steps/olmayan-id", json={"status": "RUNNING"})
    assert resp.status_code == 404


# ── Log gönderme ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_logs_returns_saved_count(app_client, pipeline_with_steps):
    _, steps = pipeline_with_steps
    install_id = steps[0]["id"]
    now = datetime.now(timezone.utc).isoformat()

    resp = await app_client.post(f"{BASE}/steps/{install_id}/logs", json={
        "lines": [
            {"line_number": 1, "stream": "stdout", "timestamp": now, "content": "Installing..."},
            {"line_number": 2, "stream": "stdout", "timestamp": now, "content": "Done."},
            {"line_number": 3, "stream": "stderr", "timestamp": now, "content": "Warning: x"},
        ]
    })
    assert resp.status_code == 201
    assert resp.json()["saved"] == 3


@pytest.mark.asyncio
async def test_add_logs_queryable_via_pipeline(app_client, pipeline_with_steps):
    pipeline_id, steps = pipeline_with_steps
    install_id = steps[0]["id"]
    now = datetime.now(timezone.utc).isoformat()

    await app_client.post(f"{BASE}/steps/{install_id}/logs", json={
        "lines": [
            {"line_number": 1, "stream": "stdout", "timestamp": now, "content": "hello"},
        ]
    })

    resp = await app_client.get(f"/api/v1/pipelines/{pipeline_id}/logs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["content"] == "hello"


@pytest.mark.asyncio
async def test_add_logs_to_nonexistent_step(app_client):
    now = datetime.now(timezone.utc).isoformat()
    resp = await app_client.post(f"{BASE}/steps/olmayan-id/logs", json={
        "lines": [{"line_number": 1, "stream": "stdout", "timestamp": now, "content": "x"}]
    })
    assert resp.status_code == 404


# ── Pipeline durumu güncelleme ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_update_to_success(app_client, pipeline_with_steps):
    pipeline_id, _ = pipeline_with_steps
    now = datetime.now(timezone.utc).isoformat()

    resp = await app_client.patch(f"{BASE}/pipelines/{pipeline_id}", json={
        "status": "SUCCESS",
        "finished_at": now,
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"
    assert resp.json()["pipeline_id"] == pipeline_id


@pytest.mark.asyncio
async def test_pipeline_update_to_failed(app_client, pipeline_with_steps):
    pipeline_id, _ = pipeline_with_steps

    resp = await app_client.patch(f"{BASE}/pipelines/{pipeline_id}", json={
        "status": "FAILED",
        "finished_at": datetime.now(timezone.utc).isoformat(),
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "FAILED"


@pytest.mark.asyncio
async def test_pipeline_update_nonexistent(app_client):
    resp = await app_client.patch(f"{BASE}/pipelines/olmayan-id", json={
        "status": "SUCCESS",
        "finished_at": datetime.now(timezone.utc).isoformat(),
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pipeline_success_visible_in_detail(app_client, pipeline_with_steps):
    pipeline_id, _ = pipeline_with_steps
    now = datetime.now(timezone.utc).isoformat()

    await app_client.patch(f"{BASE}/pipelines/{pipeline_id}", json={
        "status": "SUCCESS", "finished_at": now
    })

    detail = await app_client.get(f"/api/v1/pipelines/{pipeline_id}")
    assert detail.json()["status"] == "SUCCESS"
