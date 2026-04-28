import pytest


REPO_URL = "https://github.com/org/repo"
BRANCH = "main"


# ── Yardımcı ─────────────────────────────────────────────────────────────────

async def create_pipeline(client, repo_url=REPO_URL, branch=BRANCH):
    resp = await client.post("/api/v1/pipelines", json={"repo_url": repo_url, "branch": branch})
    assert resp.status_code == 201
    return resp.json()


# ── Pipeline oluşturma ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_pipeline_returns_queued(app_client, mock_redis):
    data = await create_pipeline(app_client)
    assert data["status"] == "QUEUED"
    assert data["trigger_type"] == "manual"
    assert data["branch"] == BRANCH
    assert "id" in data


@pytest.mark.asyncio
async def test_create_pipeline_pushes_to_redis(app_client, mock_redis):
    await create_pipeline(app_client)
    mock_redis.rpush.assert_called_once()
    queue_name = mock_redis.rpush.call_args[0][0]
    assert queue_name == "pipeline_jobs"


@pytest.mark.asyncio
async def test_create_pipeline_webhook_trigger(app_client):
    resp = await app_client.post("/api/v1/pipelines", json={
        "repo_url": REPO_URL,
        "branch": "develop",
        "commit_hash": "abc123",
        "commit_msg": "feat: new feature",
        "commit_author": "Irmak",
        "trigger_type": "webhook",
    })
    assert resp.status_code == 201
    assert resp.json()["trigger_type"] == "webhook"


# ── Pipeline listeleme ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_pipelines_empty(app_client):
    resp = await app_client.get("/api/v1/pipelines")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_list_pipelines_returns_created(app_client):
    await create_pipeline(app_client)
    await create_pipeline(app_client, branch="develop")

    resp = await app_client.get("/api/v1/pipelines")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


@pytest.mark.asyncio
async def test_list_pipelines_status_filter(app_client):
    await create_pipeline(app_client)

    resp = await app_client.get("/api/v1/pipelines?status=QUEUED")
    assert resp.json()["total"] == 1

    resp = await app_client.get("/api/v1/pipelines?status=RUNNING")
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_pipelines_pagination(app_client):
    for _ in range(5):
        await create_pipeline(app_client)

    resp = await app_client.get("/api/v1/pipelines?page=1&page_size=3")
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 3
    assert body["page"] == 1
    assert body["page_size"] == 3


# ── Pipeline detay ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_pipeline_detail(app_client):
    created = await create_pipeline(app_client)
    pipeline_id = created["id"]

    resp = await app_client.get(f"/api/v1/pipelines/{pipeline_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == pipeline_id
    assert len(body["steps"]) == 3
    step_names = [s["name"] for s in body["steps"]]
    assert step_names == ["install", "build", "test"]
    assert all(s["status"] == "PENDING" for s in body["steps"])


@pytest.mark.asyncio
async def test_get_pipeline_not_found(app_client):
    resp = await app_client.get("/api/v1/pipelines/olmayan-uuid")
    assert resp.status_code == 404


# ── Pipeline durdurma ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stop_queued_pipeline(app_client, mock_redis):
    created = await create_pipeline(app_client)
    pipeline_id = created["id"]

    resp = await app_client.post(f"/api/v1/pipelines/{pipeline_id}/stop")
    assert resp.status_code == 200
    assert resp.json()["status"] == "STOPPED"

    # Redis'e stop sinyali yazıldı mı?
    mock_redis.set.assert_called_once()
    key = mock_redis.set.call_args[0][0]
    assert key == f"pipeline_stop:{pipeline_id}"


@pytest.mark.asyncio
async def test_stop_nonexistent_pipeline(app_client):
    resp = await app_client.post("/api/v1/pipelines/olmayan-id/stop")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stop_already_stopped_pipeline(app_client):
    created = await create_pipeline(app_client)
    pipeline_id = created["id"]

    await app_client.post(f"/api/v1/pipelines/{pipeline_id}/stop")
    # İkinci durdurma isteği çakışma döndürmeli
    resp = await app_client.post(f"/api/v1/pipelines/{pipeline_id}/stop")
    assert resp.status_code == 409


# ── Kimlik doğrulama kontrolü ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_endpoints_require_auth():
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    from app.api.pipelines import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/pipelines")
        assert resp.status_code in (401, 403)
