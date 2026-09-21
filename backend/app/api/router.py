from fastapi import APIRouter

from backend.app.api import (
    auth,
    code_assistant,
    comparisons,
    documents,
    external,
    papers,
    projects,
    research_experiments,
    research_gaps,
    research_ideas,
    research_sessions,
    users,
)
from backend.app.core.config import settings
from backend.app.api import (
    research_sessions,
)

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

api_router.include_router(
    research_sessions.router
)

api_router.include_router(
    comparisons.router
)

api_router.include_router(
    research_gaps.router
)

api_router.include_router(
    research_ideas.router
)

api_router.include_router(
    research_experiments.router
)
api_router.include_router(
    code_assistant.router
)