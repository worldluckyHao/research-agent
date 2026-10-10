from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from backend.app.core.redis import (
    create_redis_client,
)
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
from backend.app.storage.factory import (
    create_storage_backend,
)
from backend.app.observability.langsmith import (
    shutdown_langsmith,
    validate_langsmith_configuration,
)

from backend.app.observability.middleware import (
    LangSmithTracingMiddleware,
)
from fastapi.middleware.cors import CORSMiddleware
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

    # LangSmith 关闭时不要求 API Key；
    # 开启时提前检查配置。
    validate_langsmith_configuration()

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

    # Redis Client 与 Application 生命周期一致。
    app.state.redis = create_redis_client()

    # 启动阶段确认 Redis 可以访问。
    await app.state.redis.ping()

    # File Storage Backend。
    #
    # Day23 当前是 LocalStorage，
    # 后续可以切换 S3 / MinIO。
    app.state.storage = (
        create_storage_backend()
    )

    yield

    # 先尽量 Flush LangSmith Trace。
    await shutdown_langsmith()

    # Shutdown
    await app.state.redis.aclose()

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
# Observability
# ============================================================

# ============================================================
# CORS
# ============================================================
#
# 前端运行在：
#     http://localhost:3000
#
# 后端运行在：
#     http://127.0.0.1:8000
#
# 两者属于不同 Origin，因此浏览器发送 JSON、
# Authorization Header 等请求时可能先发送 OPTIONS
# 预检请求。
#
# CORSMiddleware 统一处理这些跨域请求，
# 不需要手动编写 OPTIONS 路由。
#
app.add_middleware(
    CORSMiddleware,

    # 允许的前端 Origin 从配置读取。
    allow_origins=(
        settings.CORS_ORIGINS_LIST
    ),

    # 允许携带 Cookie / Authorization 等凭证信息。
    allow_credentials=True,

    # 开发阶段允许所有 HTTP Method，
    # 后续 POST / PATCH / DELETE 都不会再被 CORS 卡住。
    allow_methods=[
        "*"
    ],

    # 允许 Content-Type、Authorization 等请求头。
    allow_headers=[
        "*"
    ],
)


# ============================================================
# Observability
# ============================================================

app.add_middleware(
    LangSmithTracingMiddleware
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