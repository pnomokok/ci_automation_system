import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from unittest.mock import AsyncMock, patch

from app.models import Base

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def mock_github_validation():
    with patch(
        "app.services.repository_service._assert_public_github_repo",
        new=AsyncMock(return_value=None),
    ):
        yield


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB, echo=False)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.rpush = AsyncMock(return_value=1)
    redis.set = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    return redis


@pytest_asyncio.fixture
async def app_client(db_session, mock_redis):
    from fastapi import FastAPI
    from app.api.auth import router as auth_router
    from app.api.pipelines import router as pipeline_router
    from app.api.repositories import router as repositories_router
    from app.api.internal.steps import router as internal_steps_router
    from app.api.internal.pipelines import router as internal_pipelines_router
    from app.core.deps import get_db, get_current_user
    from app.core.redis import get_redis
    from app.core.security import hash_password
    from app.repositories.user_repo import UserRepository
    from app.models.user import User

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(pipeline_router, prefix="/api/v1")
    app.include_router(repositories_router, prefix="/api/v1")
    app.include_router(internal_steps_router, prefix="/api/v1/internal")
    app.include_router(internal_pipelines_router, prefix="/api/v1/internal")

    # Test kullanıcısı
    user_repo = UserRepository()
    test_user = await user_repo.create(db_session, "test_user", hash_password("test_pass"))
    await db_session.commit()

    async def override_db():
        yield db_session

    async def override_redis():
        return mock_redis

    async def override_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = override_redis
    app.dependency_overrides[get_current_user] = override_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def with_test_repo(app_client):
    """Pipeline testleri için varsayılan test repo'sunu oluşturur (test_user owner olur)."""
    await app_client.post("/api/v1/repositories", json={
        "url": "https://github.com/org/repo",
        "default_branch": "main",
        "webhook_secret": "test-secret",
    })


@pytest_asyncio.fixture
async def other_member_client(db_session, mock_redis):
    """Repoya member olarak eklenmiş başka bir kullanıcının client'ı."""
    from fastapi import FastAPI
    from app.api.auth import router as auth_router
    from app.api.pipelines import router as pipeline_router
    from app.api.repositories import router as repositories_router
    from app.api.internal.steps import router as internal_steps_router
    from app.api.internal.pipelines import router as internal_pipelines_router
    from app.core.deps import get_db, get_current_user
    from app.core.redis import get_redis
    from app.core.security import hash_password
    from app.repositories.user_repo import UserRepository

    user_repo = UserRepository()
    other_user = await user_repo.create(db_session, "other_user", hash_password("other_pass"))
    await db_session.commit()

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(pipeline_router, prefix="/api/v1")
    app.include_router(repositories_router, prefix="/api/v1")
    app.include_router(internal_steps_router, prefix="/api/v1/internal")
    app.include_router(internal_pipelines_router, prefix="/api/v1/internal")

    async def override_db():
        yield db_session

    async def override_redis():
        return mock_redis

    async def override_current_user():
        return other_user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = override_redis
    app.dependency_overrides[get_current_user] = override_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, other_user.username
