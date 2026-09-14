from fastapi import APIRouter

from backend.app.api import (
    auth,
    documents,
    external,
    papers,
    projects,
    users,
)
from backend.app.core.config import settings


api_router = APIRouter(
    prefix=settings.API_V1_PREFIX
)


api_router.include_router(
    auth.router
)

api_router.include_router(
    papers.router
)

api_router.include_router(
    documents.router
)

api_router.include_router(
    projects.router
)

api_router.include_router(
    external.router
)

api_router.include_router(
    users.router
)