from fastapi import APIRouter

from backend.app.api import papers
from backend.app.core.config import settings


# ============================================================
# API 总 Router
# ============================================================
#
# settings.API_V1_PREFIX 默认：
#
# /api/v1
#
# 所以这里最终仍然是：
#
# /api/v1
#
api_router = APIRouter(
    prefix=settings.API_V1_PREFIX
)


# ============================================================
# 注册 Paper Router
# ============================================================
#
# papers.py 自己的 prefix：
#
# /papers
#
# 两层 Router 拼起来：
#
# /api/v1
# +
# /papers
#
# =
#
# /api/v1/papers
#
api_router.include_router(
    papers.router
)