from contextlib import asynccontextmanager
import httpx
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
from backend.app.clients.arxiv import ArxivClient

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
    管理数据库连接池和外部 HTTP 连接池生命周期。
    """

    # 分别控制网络各阶段 timeout。
    timeout = httpx.Timeout(
        connect=settings.HTTP_CONNECT_TIMEOUT,
        read=settings.HTTP_READ_TIMEOUT,
        write=settings.HTTP_WRITE_TIMEOUT,
        pool=settings.HTTP_POOL_TIMEOUT,
    )

    # 控制连接池规模，避免无界创建连接。
    limits = httpx.Limits(
        max_connections=settings.HTTP_MAX_CONNECTIONS,
        max_keepalive_connections=(
            settings.HTTP_MAX_KEEPALIVE_CONNECTIONS
        ),
    )

    # 整个 FastAPI 生命周期共享一个 AsyncClient。
    app.state.http_client = httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        follow_redirects=True,
    )

    # arXiv Client 保持应用级状态，
    # 这样限流 Lock 和请求时间才能跨 Request 生效。
    app.state.arxiv_client = ArxivClient(
        client=app.state.http_client
    )

    yield

    # 关闭 HTTP 连接池。
    await app.state.http_client.aclose()

    # 关闭数据库连接池。
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