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
# settings.DEBUG = True
#     → DEBUG 日志
#
# settings.DEBUG = False
#     → INFO 日志
#
setup_logging(
    debug=settings.DEBUG
)


# ============================================================
# FastAPI 生命周期管理
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Application 生命周期。

    Day6 开始以后：

    不再使用：

        Base.metadata.create_all()

    创建数据库表。

    因为数据库 Schema 已经正式交给：

        Alembic

    管理。

    所以这里启动阶段暂时没有额外数据库操作。
    """

    # -------------------------
    # FastAPI 启动阶段
    # -------------------------

    yield

    # -------------------------
    # FastAPI 关闭阶段
    # -------------------------
    #
    # 释放 SQLAlchemy AsyncEngine 的连接池资源。
    await engine.dispose()


# ============================================================
# 创建 FastAPI Application
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)


# ============================================================
# 注册统一业务异常 Handler
# ============================================================
#
# 所有 AppException 的子类都会进入：
#
# app_exception_handler
#
# 例如：
#
# PaperNotFoundException
# PaperDOIExistsException
# EmptyUpdateException
#
app.add_exception_handler(
    AppException,
    app_exception_handler,
)


# ============================================================
# 注册未知异常兜底 Handler
# ============================================================
#
# 如果某个 Exception 没有被前面的业务 Handler 处理，
# 最后就会进入这里。
#
# 返回：
#
# 500 Internal Server Error
#
app.add_exception_handler(
    Exception,
    unhandled_exception_handler,
)


# ============================================================
# 注册 API Router
# ============================================================
#
# api_router 中目前会继续包含：
#
# /api/v1/papers/
#
app.include_router(api_router)


# ============================================================
# 健康检查接口
# ============================================================

@app.get("/health")
async def health_check():
    """
    用于检查 FastAPI 服务是否正常运行。
    """

    return {
        "status": "ok"
    }