import pytest

pytestmark = pytest.mark.usefixtures("with_test_repo")

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
    for i in range(5):
        await create_pipeline(app_client, branch=f"page-branch-{i}")

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
    # İkinci durdurma isteği INVALID_STATE döndürmeli
    resp = await app_client.post(f"/api/v1/pipelines/{pipeline_id}/stop")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INVALID_STATE"


# ── Aynı branch için tekrar pipeline oluşturma ───────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_queued_pipeline_rejected(app_client):
    """Aynı repo+branch için QUEUED pipeline varken yeni istek 409 dönmeli."""
    await create_pipeline(app_client)  # ilk pipeline → QUEUED

    resp = await app_client.post(
        "/api/v1/pipelines",
        json={"repo_url": REPO_URL, "branch": BRANCH},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "ALREADY_RUNNING"


@pytest.mark.asyncio
async def test_duplicate_running_pipeline_rejected(app_client):
    """Aynı repo+branch için RUNNING pipeline varken yeni istek 409 dönmeli."""
    created = await create_pipeline(app_client)
    await app_client.patch(
        f"/api/v1/internal/pipelines/{created['id']}",
        json={"status": "RUNNING"},
    )

    resp = await app_client.post(
        "/api/v1/pipelines",
        json={"repo_url": REPO_URL, "branch": BRANCH},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_different_branch_allowed_while_queued(app_client):
    """Aynı repo'nun farklı branch'i QUEUED olsa bile yeni pipeline oluşturulabilmeli."""
    await create_pipeline(app_client, branch="main")

    resp = await app_client.post(
        "/api/v1/pipelines",
        json={"repo_url": REPO_URL, "branch": "develop"},
    )
    assert resp.status_code == 201


# ── Eşzamanlılık limiti ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_max_concurrent_pipelines_enforced(app_client):
    """MAX_CONCURRENT_PIPELINES (3) aşıldığında 409 MAX_PIPELINES_REACHED dönmeli."""
    # 3 pipeline oluştur, hepsini RUNNING'e geçir
    pipeline_ids = []
    for i in range(3):
        p = await create_pipeline(app_client, branch=f"branch-{i}")
        pipeline_ids.append(p["id"])

    for pid in pipeline_ids:
        resp = await app_client.patch(
            f"/api/v1/internal/pipelines/{pid}",
            json={"status": "RUNNING"},
        )
        assert resp.status_code == 200

    # 4. pipeline → limit aşıldı
    resp = await app_client.post(
        "/api/v1/pipelines",
        json={"repo_url": REPO_URL, "branch": "branch-overflow"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "MAX_PIPELINES_REACHED"


@pytest.mark.asyncio
async def test_max_concurrent_allows_after_finish(app_client):
    """Bir pipeline bittikten sonra yeni pipeline kabul edilmeli."""
    pipeline_ids = []
    for i in range(3):
        p = await create_pipeline(app_client, branch=f"fin-branch-{i}")
        pipeline_ids.append(p["id"])

    for pid in pipeline_ids:
        await app_client.patch(
            f"/api/v1/internal/pipelines/{pid}",
            json={"status": "RUNNING"},
        )

    # Birini bitir
    await app_client.patch(
        f"/api/v1/internal/pipelines/{pipeline_ids[0]}",
        json={"status": "SUCCESS"},
    )

    # Artık yeni pipeline oluşturulabilmeli
    resp = await app_client.post(
        "/api/v1/pipelines",
        json={"repo_url": REPO_URL, "branch": "branch-new"},
    )
    assert resp.status_code == 201


# ── Rapor endpoint'i ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_empty_when_no_logs(app_client):
    created = await create_pipeline(app_client)
    resp = await app_client.get(f"/api/v1/pipelines/{created['id']}/report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_tests"] == 0
    assert body["passed"] == 0
    assert body["failed"] == 0


@pytest.mark.asyncio
async def test_report_parses_pytest_summary(app_client):
    """Test adımına pytest özet satırı loglanınca rapor doğru parse edilmeli."""
    created = await create_pipeline(app_client)
    pipeline_id = created["id"]

    # Önce test step'ini RUNNING'e geçir
    detail = await app_client.get(f"/api/v1/pipelines/{pipeline_id}")
    test_step = next(s for s in detail.json()["steps"] if s["name"] == "test")
    step_id = test_step["id"]

    await app_client.patch(
        f"/api/v1/internal/steps/{step_id}",
        json={"status": "RUNNING"},
    )

    # Pytest özet satırını log olarak gönder
    await app_client.post(
        f"/api/v1/internal/steps/{step_id}/logs",
        json={"lines": [
            {"line_number": 1, "stream": "stdout", "timestamp": "2026-01-01T00:00:00Z",
             "content": "5 passed, 2 failed, 1 skipped in 3.14s"},
        ]},
    )

    resp = await app_client.get(f"/api/v1/pipelines/{pipeline_id}/report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["passed"] == 5
    assert body["failed"] == 2
    assert body["skipped"] == 1
    assert body["total_tests"] == 8


@pytest.mark.asyncio
async def test_report_reads_all_pages_beyond_500(app_client):
    """500'den fazla log satırı olunca tüm sayfalar okunmalı, sayılar eksik kalmamalı."""
    created = await create_pipeline(app_client)
    pipeline_id = created["id"]

    detail = await app_client.get(f"/api/v1/pipelines/{pipeline_id}")
    test_step = next(s for s in detail.json()["steps"] if s["name"] == "test")
    step_id = test_step["id"]

    await app_client.patch(
        f"/api/v1/internal/steps/{step_id}",
        json={"status": "RUNNING"},
    )

    # 501 log satırı gönder: ilk 500'i gürültü, 501. satır özet
    noise_lines = [
        {"line_number": i + 1, "stream": "stdout",
         "timestamp": "2026-01-01T00:00:00Z", "content": f"test output line {i + 1}"}
        for i in range(500)
    ]
    summary_line = {
        "line_number": 501, "stream": "stdout",
        "timestamp": "2026-01-01T00:00:00Z",
        "content": "10 passed in 42.0s",
    }
    await app_client.post(
        f"/api/v1/internal/steps/{step_id}/logs",
        json={"lines": noise_lines + [summary_line]},
    )

    resp = await app_client.get(f"/api/v1/pipelines/{pipeline_id}/report")
    assert resp.status_code == 200
    body = resp.json()
    # 501. satırdaki özet okunabilmeli
    assert body["passed"] == 10, "500+ log satırında özet satırı atlanmamalı"
    assert body["total_tests"] == 10


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
