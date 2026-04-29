from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://ci_user:ci_pass@localhost:5432/ci_db"
    test_database_url: str = "sqlite+aiosqlite:///./test.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Pipeline
    max_concurrent_pipelines: int = 3
    pipeline_timeout_sec: int = 600

    # Internal service URLs
    repo_manager_url: str = "http://repo-manager:8001"


settings = Settings()
