from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.internal.pipelines import router as internal_pipelines_router
from app.api.internal.steps import router as internal_steps_router
from app.api.pipelines import router as pipelines_router
from app.api.repositories import router as repositories_router
from app.api.teams import router as teams_router
from app.core.redis import close_redis, get_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_redis()   # bağlantıyı ısıt
    yield
    await close_redis()


app = FastAPI(
    title="CI Orchestrator",
    version="1.0.0",
    description="CI Otomasyon Sistemi — Pipeline yönetim API'si",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Dashboard URL'si .env ile kısıtlanacak
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public endpoint'ler — JWT zorunlu
app.include_router(auth_router,         prefix="/api/v1")
app.include_router(pipelines_router,    prefix="/api/v1")
app.include_router(repositories_router, prefix="/api/v1")
app.include_router(teams_router,        prefix="/api/v1")

# Internal endpoint'ler — JWT yok, yalnızca Docker ağı içinden erişilir
app.include_router(internal_steps_router,     prefix="/api/v1/internal")
app.include_router(internal_pipelines_router, prefix="/api/v1/internal")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
