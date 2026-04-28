import pytest

URL = "https://github.com/org/repo"


async def create_repo(client, url=URL):
    resp = await client.post("/api/v1/repositories", json={
        "url": url,
        "default_branch": "main",
        "webhook_secret": "gizli",
    })
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_list_empty(app_client):
    resp = await app_client.get("/api/v1/repositories")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_returns_id(app_client):
    data = await create_repo(app_client)
    assert "id" in data
    assert data["url"] == URL
    assert data["default_branch"] == "main"
    assert "webhook_secret" not in data  # hassas alan dönmemeli


@pytest.mark.asyncio
async def test_list_after_create(app_client):
    await create_repo(app_client)
    await create_repo(app_client, url="https://github.com/org/repo2")
    resp = await app_client.get("/api/v1/repositories")
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_duplicate_url_returns_409(app_client):
    await create_repo(app_client)
    resp = await app_client.post("/api/v1/repositories", json={
        "url": URL,
        "default_branch": "main",
        "webhook_secret": "baska",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_existing(app_client):
    data = await create_repo(app_client)
    repo_id = data["id"]

    resp = await app_client.delete(f"/api/v1/repositories/{repo_id}")
    assert resp.status_code == 204

    repos = await app_client.get("/api/v1/repositories")
    assert repos.json() == []


@pytest.mark.asyncio
async def test_delete_nonexistent(app_client):
    resp = await app_client.delete("/api/v1/repositories/olmayan-id")
    assert resp.status_code == 404
