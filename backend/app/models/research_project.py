# backend/app/models/research_project.py

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class ResearchProject(Base):
    """
    用户创建的研究项目。

    一个 ResearchProject 可以理解成一个独立的科研工作空间，例如：
    - 多模态降水预测
    - PWformer 改进实验
    - RAIN-F 数据集实验

    Day14：
        User 1 -> N ResearchProject

    后续：
        ResearchProject <-> Paper
    """

    __tablename__ = "research_projects"

    # =========================================================
    # 1. 主键
    # =========================================================
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    # =========================================================
    # 2. 项目名称
    # =========================================================
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    # =========================================================
    # 3. 项目描述
    # =========================================================
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # =========================================================
    # 4. 项目状态
    # =========================================================
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="active",
        server_default="active",
    )

    # =========================================================
    # 5. 项目所属用户
    # =========================================================
    owner_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # =========================================================
    # 6. 创建时间
    # =========================================================
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # =========================================================
    # 7. 更新时间
    # =========================================================
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # =========================================================
    # 8. ORM Relationship
    # =========================================================
    owner: Mapped["User"] = relationship(
        back_populates="research_projects",
    )