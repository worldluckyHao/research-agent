from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.app.db.base import Base


class ResearchConversation(Base):
    """
    Conversation（对话线程）。

    一个 ResearchSession
    可以包含多个 Conversation。

    当前 Day31 可以选择绑定
    一个 PaperDocument。
    """

    __tablename__ = "research_conversations"


    id: Mapped[int] = mapped_column(
        primary_key=True,
    )


    session_id: Mapped[int] = mapped_column(
        ForeignKey(
            "research_sessions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    # --------------------------------------------------------
    # Optional Document Context
    # --------------------------------------------------------

    # Conversation 可以暂时没有 Document，
    # 为以后 Project-Level / Multi-Paper Chat
    # 保留空间。
    document_id: Mapped[
        Optional[int]
    ] = mapped_column(
        ForeignKey(
            "paper_documents.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )


    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="New conversation",
        server_default="New conversation",
    )


    # --------------------------------------------------------
    # Message Sequence
    # --------------------------------------------------------

    # 下一个 Message 使用的序号。
    #
    # 不依赖：
    # SELECT MAX(sequence_number)
    #
    # 后续配合 Row Lock，
    # 避免并发消息生成相同序号。
    next_sequence_number: Mapped[
        int
    ] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
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

    session: Mapped[
        "ResearchSession"
    ] = relationship(
        back_populates="conversations",
    )


    document = relationship(
        "PaperDocument",
        lazy="selectin",
    )


    messages: Mapped[
        list["ResearchMessage"]
    ] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )