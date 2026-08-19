from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from backend.app.schemas.paper import PaperResponse


class ResearchProjectCreate(BaseModel):
    """
    创建 ResearchProject。
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    name: str = Field(
        min_length=3,
        max_length=200,
    )

    description: Optional[str] = Field(
        default=None,
        max_length=5000,
    )


class ResearchProjectUpdate(BaseModel):
    """
    PATCH 更新 ResearchProject。
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    name: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=200,
    )

    description: Optional[str] = Field(
        default=None,
        max_length=5000,
    )


class ResearchProjectResponse(BaseModel):
    """
    Project 基础返回结构。
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    name: str
    description: Optional[str] = None
    owner_id: int
    created_at: datetime
    updated_at: datetime


class ResearchProjectListResponse(BaseModel):
    """
    Project 分页列表。
    """

    items: list[ResearchProjectResponse]

    total: int
    page: int
    page_size: int
    pages: int


# ============================================================
# Day15
# ============================================================

class ProjectPaperResponse(BaseModel):
    """
    Project 中的一篇 Paper，同时返回加入时间。
    """

    paper: PaperResponse
    added_at: datetime


class ProjectPaperListResponse(BaseModel):
    """
    Project Papers 分页列表。
    """

    items: list[ProjectPaperResponse]

    total: int
    page: int
    page_size: int
    pages: int