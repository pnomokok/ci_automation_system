import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models import Base
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.repositories.user_repo import UserRepository

TEST_DB = "sqlite+aiosqlite:///:memory:"


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB, echo=False)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def app_client(db_session):
    """FastAPI test client — get_db bağımlılığını test DB ile ezer."""
    from fastapi import FastAPI
    from app.api.auth import router
    from app.core.deps import get_db

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# ── Security unit testleri ────────────────────────────────────────────────────

def test_password_hash_and_verify():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed) is True
    assert verify_password("yanlis", hashed) is False


def test_create_and_decode_token():
    token = create_access_token(subject="user-id-1", username="irmak")
    payload = decode_token(token)
    assert payload["sub"] == "user-id-1"
    assert payload["username"] == "irmak"


def test_decode_invalid_token():
    from jose import JWTError
    with pytest.raises(JWTError):
        decode_token("bu.gecersiz.token")


# ── Auth endpoint testleri ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(app_client, db_session):
    user_repo = UserRepository()
    await user_repo.create(db_session, "irmak", hash_password("sifre123"))
    await db_session.commit()

    resp = await app_client.post("/api/v1/auth/login", json={"username": "irmak", "password": "sifre123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password(app_client, db_session):
    user_repo = UserRepository()
    await user_repo.create(db_session, "irmak2", hash_password("dogru"))
    await db_session.commit()

    resp = await app_client.post("/api/v1/auth/login", json={"username": "irmak2", "password": "yanlis"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(app_client):
    resp = await app_client.post("/api/v1/auth/login", json={"username": "yok", "password": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_success(app_client, db_session):
    user_repo = UserRepository()
    await user_repo.create(db_session, "irmak3", hash_password("sifre"))
    await db_session.commit()

    login_resp = await app_client.post("/api/v1/auth/login", json={"username": "irmak3", "password": "sifre"})
    token = login_resp.json()["access_token"]

    resp = await app_client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_refresh_invalid_token(app_client):
    resp = await app_client.post("/api/v1/auth/refresh", json={"refresh_token": "gecersiz.token.burada"})
    assert resp.status_code == 401


# ── Register endpoint testleri ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_creates_user(app_client):
    resp = await app_client.post("/api/v1/auth/register", json={"username": "yeni_user", "password": "guclu_sifre"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "yeni_user"
    assert "id" in body


@pytest.mark.asyncio
async def test_register_duplicate_username_rejected(app_client):
    await app_client.post("/api/v1/auth/register", json={"username": "tekrar", "password": "sifre1"})
    resp = await app_client.post("/api/v1/auth/register", json={"username": "tekrar", "password": "sifre2"})
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "USERNAME_TAKEN"


@pytest.mark.asyncio
async def test_register_then_login(app_client):
    await app_client.post("/api/v1/auth/register", json={"username": "fullflow", "password": "pass123"})
    resp = await app_client.post("/api/v1/auth/login", json={"username": "fullflow", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
