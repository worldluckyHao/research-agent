from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# 创建 Project 时使用
# ============================================================
class ResearchProjectCreate(BaseModel):
    """
    POST /projects/
    请求体使用的 Schema。
    """

    name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="研究项目名称",
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
        description="研究项目描述",
    )

    model_config = ConfigDict(
        extra="forbid",
    )


# ============================================================
# 修改 Project 时使用
# ============================================================
class ResearchProjectUpdate(BaseModel):
    """
    PATCH /projects/{project_id}
    请求体使用的 Schema。

    PATCH 是部分更新，因此字段都不是必填项。
    """

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )

    status: Literal[
                "active",
                "completed",
                "archived",
            ] | None = None

    model_config = ConfigDict(
        extra="forbid",
    )


# ============================================================
# API 返回 Project 时使用
# ============================================================
class ResearchProjectResponse(BaseModel):
    """
    Project API 返回数据。
    """

    id: int

    name: str

    description: str | None

    status: str

    owner_id: int

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )