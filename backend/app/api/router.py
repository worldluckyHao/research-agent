from fastapi import APIRouter

from backend.app.api import (
    auth,
    papers,
    projects,
    users,
)
from backend.app.core.config import settings


# ============================================================
# API v1 Root Router
# ============================================================

api_router = APIRouter(
    prefix=settings.API_V1_PREFIX
)
# ============================================================
# Research Project API
# ============================================================

api_router.include_router(
    projects.router
)

# ============================================================
# Authentication API
# ============================================================
#
# 最终：
#
# POST /api/v1/auth/login
#
api_router.include_router(
    auth.router
)


# ============================================================
# Paper API
# ============================================================

api_router.include_router(
    papers.router
)


# ============================================================
# User API
# ============================================================
#
# POST /api/v1/users/register
#
# GET /api/v1/users/me
#
api_router.include_router(
    users.router
)