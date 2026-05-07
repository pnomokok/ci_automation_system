import pytest

TEAM_NAME = "alpha-team"
REPO_URL = "https://github.com/test/repo"


async def register_user(client, username, password="pass1234"):
    resp = await client.post("/api/v1/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 201
    return resp.json()


async def create_team(client, name=TEAM_NAME):
    resp = await client.post("/api/v1/teams", json={"name": name})
    assert resp.status_code == 201
    return resp.json()


# ── Takım oluşturma ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_team(app_client):
    team = await create_team(app_client)
    assert team["name"] == TEAM_NAME
    assert "id" in team


@pytest.mark.asyncio
async def test_create_team_duplicate_rejected(app_client):
    await create_team(app_client)
    resp = await app_client.post("/api/v1/teams", json={"name": TEAM_NAME})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "TEAM_NAME_TAKEN"


@pytest.mark.asyncio
async def test_creator_is_auto_member(app_client):
    team = await create_team(app_client)
    resp = await app_client.get(f"/api/v1/teams/{team['id']}/members")
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 1
    assert members[0]["username"] == "test_user"


# ── Üye ekleme/çıkarma ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_member(app_client, db_session):
    await register_user(app_client, "new_member")
    team = await create_team(app_client)

    resp = await app_client.post(
        f"/api/v1/teams/{team['id']}/members",
        json={"username": "new_member"},
    )
    assert resp.status_code == 201

    members = (await app_client.get(f"/api/v1/teams/{team['id']}/members")).json()
    assert any(m["username"] == "new_member" for m in members)


@pytest.mark.asyncio
async def test_add_duplicate_member_rejected(app_client):
    team = await create_team(app_client)
    resp = await app_client.post(
        f"/api/v1/teams/{team['id']}/members",
        json={"username": "test_user"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "ALREADY_MEMBER"


@pytest.mark.asyncio
async def test_remove_member(app_client):
    await register_user(app_client, "to_remove")
    team = await create_team(app_client)

    add = await app_client.post(
        f"/api/v1/teams/{team['id']}/members",
        json={"username": "to_remove"},
    )
    user_id = add.json()["user_id"]

    resp = await app_client.delete(f"/api/v1/teams/{team['id']}/members/{user_id}")
    assert resp.status_code == 204

    members = (await app_client.get(f"/api/v1/teams/{team['id']}/members")).json()
    assert not any(m["user_id"] == user_id for m in members)


# ── Pipeline takım izolasyonu ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_visible_to_team_member(app_client, mock_redis):
    team = await create_team(app_client)

    resp = await app_client.post("/api/v1/pipelines", json={
        "repo_url": REPO_URL,
        "branch": "main",
        "team_id": team["id"],
    })
    assert resp.status_code == 201

    pipelines = (await app_client.get("/api/v1/pipelines")).json()
    assert pipelines["total"] == 1


@pytest.mark.asyncio
async def test_pipeline_with_team_hidden_from_non_member(app_client, mock_redis, db_session):
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    from app.api.auth import router as auth_router
    from app.api.pipelines import router as pipeline_router
    from app.api.teams import router as teams_router
    from app.core.deps import get_db, get_current_user
    from app.core.redis import get_redis
    from app.core.security import hash_password
    from app.repositories.user_repo import UserRepository

    # Farklı kullanıcı için ayrı client oluştur
    user_repo = UserRepository()
    other = await user_repo.create(db_session, "other_user", hash_password("pass"))
    await db_session.commit()

    other_app = FastAPI()
    other_app.include_router(auth_router, prefix="/api/v1")
    other_app.include_router(pipeline_router, prefix="/api/v1")
    other_app.include_router(teams_router, prefix="/api/v1")

    async def override_db():
        yield db_session

    async def override_redis():
        return mock_redis

    async def override_other_user():
        return other

    other_app.dependency_overrides[get_db] = override_db
    other_app.dependency_overrides[get_redis] = override_redis
    other_app.dependency_overrides[get_current_user] = override_other_user

    # Takım sahibi (test_user) pipeline oluştursun
    team = await create_team(app_client)
    await app_client.post("/api/v1/pipelines", json={
        "repo_url": REPO_URL, "branch": "main", "team_id": team["id"],
    })

    # Takım dışındaki kullanıcı pipeline'ı görememeli
    async with AsyncClient(transport=ASGITransport(app=other_app), base_url="http://test") as other_client:
        resp = await other_client.get("/api/v1/pipelines")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_pipeline_without_team_visible_to_all(app_client, mock_redis, db_session):
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    from app.api.pipelines import router as pipeline_router
    from app.core.deps import get_db, get_current_user
    from app.core.redis import get_redis
    from app.core.security import hash_password
    from app.repositories.user_repo import UserRepository

    user_repo = UserRepository()
    stranger = await user_repo.create(db_session, "stranger_user", hash_password("pass"))
    await db_session.commit()

    stranger_app = FastAPI()
    stranger_app.include_router(pipeline_router, prefix="/api/v1")

    async def override_db():
        yield db_session

    async def override_redis():
        return mock_redis

    async def override_stranger():
        return stranger

    stranger_app.dependency_overrides[get_db] = override_db
    stranger_app.dependency_overrides[get_redis] = override_redis
    stranger_app.dependency_overrides[get_current_user] = override_stranger

    # team_id olmadan pipeline oluştur
    await app_client.post("/api/v1/pipelines", json={
        "repo_url": REPO_URL, "branch": "main",
    })

    # Takımsız pipeline herkese görünür
    async with AsyncClient(transport=ASGITransport(app=stranger_app), base_url="http://test") as stranger_client:
        resp = await stranger_client.get("/api/v1/pipelines")
        assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_non_member_cannot_create_pipeline_for_team(app_client, mock_redis, db_session):
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    from app.api.pipelines import router as pipeline_router
    from app.core.deps import get_db, get_current_user
    from app.core.redis import get_redis
    from app.core.security import hash_password
    from app.repositories.user_repo import UserRepository

    user_repo = UserRepository()
    outsider = await user_repo.create(db_session, "outsider_user", hash_password("pass"))
    await db_session.commit()

    outsider_app = FastAPI()
    outsider_app.include_router(pipeline_router, prefix="/api/v1")

    async def override_db():
        yield db_session

    async def override_redis():
        return mock_redis

    async def override_outsider():
        return outsider

    outsider_app.dependency_overrides[get_db] = override_db
    outsider_app.dependency_overrides[get_redis] = override_redis
    outsider_app.dependency_overrides[get_current_user] = override_outsider

    team = await create_team(app_client)

    async with AsyncClient(transport=ASGITransport(app=outsider_app), base_url="http://test") as outsider_client:
        resp = await outsider_client.post("/api/v1/pipelines", json={
            "repo_url": REPO_URL, "branch": "main", "team_id": team["id"],
        })
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"
