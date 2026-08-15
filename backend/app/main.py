from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from backend.app.api.router import api_router
from backend.app.dependencies import get_db
from backend.app.models.paper import Paper
from backend.app.db.session import engine
from backend.app.db.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):

    yield

    await engine.dispose()

app = FastAPI(
    title="Research Agent API",
    lifespan=lifespan,
)


# 注册 API 路由
app.include_router(
    api_router,
    prefix="/api/v1",
)


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


@app.get("/health/db")
async def database_health(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT 1")
    )

    value = result.scalar_one()

    return {
        "status": "ok",
        "database": value,
    }