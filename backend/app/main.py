from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.core.exceptions import (
    AppException,
    app_exception_handler,
    unhandled_exception_handler,
)
from backend.app.core.logging import setup_logging
from backend.app.db.session import engine


# ============================================================
# 初始化日志系统
# ============================================================
#
# 日志等级现在不再直接依赖 DEBUG，
# 而是由：
#
# backend/.env
#
# LOG_LEVEL=DEBUG
#
# 控制。
#
setup_logging(
    level=settings.LOG_LEVEL
)


# ============================================================
# FastAPI 生命周期
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理。

    启动阶段：
        暂时不需要特殊操作。

    注意：
        Day6 开始数据库 Schema 已经完全交给 Alembic，
        所以这里绝对不要重新加入：

        Base.metadata.create_all()

    关闭阶段：
        释放 SQLAlchemy Engine 连接池。
    """

    # -------------------------
    # Application startup
    # -------------------------

    yield

    # -------------------------
    # Application shutdown
    # -------------------------

    await engine.dispose()


# ============================================================
# 创建 FastAPI Application
# ============================================================

app = FastAPI(
    # 从 Settings 读取应用名称。
    title=settings.APP_NAME,

    # 从 Settings 读取版本。
    version=settings.APP_VERSION,

    # 开发环境通常 True；
    # 正式环境应该 False。
    debug=settings.DEBUG,

    # 生命周期管理。
    lifespan=lifespan,
)


# ============================================================
# Day9：业务异常 Handler
# ============================================================

app.add_exception_handler(
    AppException,
    app_exception_handler,
)


# ============================================================
# Day9：未知异常 Handler
# ============================================================

app.add_exception_handler(
    Exception,
    unhandled_exception_handler,
)


# ============================================================
# 注册 API
# ============================================================

app.include_router(
    api_router
)


# ============================================================
# Health Check
# ============================================================

@app.get(
    "/health",
    tags=["health"],
)
async def health_check():
    """
    检查 Research Agent API 是否正常运行。

    以后 Docker / Nginx / 云服务器
    也可以使用这个接口进行健康检查。
    """

    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }