from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.app.db.base import Base


class ResearchSession(Base):
    """
    Research Session（研究会话）。

    代表一个较大的科研工作空间。

    一个 User：
        可以拥有多个 ResearchSession。

    一个 ResearchSession：
        可以拥有多个 Conversation。
    """

    __tablename__ = "research_sessions"


    id: Mapped[int] = mapped_column(
        primary_key=True,
    )


    owner_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )


    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


    updated_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


    # --------------------------------------------------------
    # Relationships
    # --------------------------------------------------------

    owner = relationship(
        "User",
    )


    conversations: Mapped[
        list["ResearchConversation"]
    ] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )