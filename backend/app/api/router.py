from fastapi import APIRouter

from backend.app.api import papers


api_router = APIRouter()


api_router.include_router(
    papers.router
)