from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    DateTime,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.app.db.base import Base
from backend.app.models.associations import (
    user_saved_papers,
)
from backend.app.schemas.paper import (
    PaperResponse,
)


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint(
            "username",
            name="uq_users_username",
        ),
        UniqueConstraint(
            "email",
            name="uq_users_email",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # 数据库只保存密码 Hash。
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )


    # ========================================================
    # User -> Paper 一对多
    # ========================================================

    # 当前用户创建的 Papers。
    papers: Mapped[list["Paper"]] = relationship(
        back_populates="owner",
        lazy="selectin",
    )


    # ========================================================
    # User <-> Paper 多对多
    # ========================================================

    # 当前用户收藏的 Papers。
    saved_papers: Mapped[list["Paper"]] = relationship(
        secondary=user_saved_papers,
        back_populates="saved_by_users",
        lazy="selectin",
    )

    # 一个用户可以拥有多个研究项目
    research_projects: Mapped[list["ResearchProject"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

