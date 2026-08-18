from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
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


class Paper(Base):
    __tablename__ = "papers"

    __table_args__ = (
        UniqueConstraint(
            "doi",
            name="uq_papers_doi",
        ),
        CheckConstraint(
            "year >= 1900 AND year <= 2100",
            name="ck_papers_year_range",
        ),
        Index(
            "ix_papers_year",
            "year",
        ),
        Index(
            "ix_papers_source",
            "source",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    authors: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    doi: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )

    source: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    abstract: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    keywords: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    language: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="en",
    )


    # ========================================================
    # User -> Paper 一对多
    # ========================================================

    # nullable=True：
    # 兼容 Day1-Day12 已存在、没有 owner 的旧论文。
    owner_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )


    # ========================================================
    # Relationship
    # ========================================================

    # paper.owner -> User
    owner: Mapped[Optional["User"]] = relationship(
        back_populates="papers",
    )

    # 收藏这篇 Paper 的所有 User。
    saved_by_users: Mapped[list["User"]] = relationship(
        secondary=user_saved_papers,
        back_populates="saved_papers",
        lazy="selectin",
    )


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )