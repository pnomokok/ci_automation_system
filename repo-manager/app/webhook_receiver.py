from fastapi import FastAPI

from app.API import trigger_router, webhook_router

app = FastAPI(title="Repository Manager", version="1.0.0")
app.include_router(webhook_router)
app.include_router(trigger_router)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
