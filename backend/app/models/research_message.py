from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import (
    JSONB,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.app.db.base import Base


class ResearchMessage(Base):
    """
    Research Conversation Message
    （研究对话消息）。

    支持角色：

        user
        assistant
        system
        tool

    Day32 新增：

        prompt_id
        prompt_version

    用于记录生成该 Assistant Message
    时采用的 Prompt Provenance。
    """

    __tablename__ = "research_messages"


    __table_args__ = (

        # 一个 Conversation 内，
        # sequence_number 必须唯一。
        UniqueConstraint(
            "conversation_id",
            "sequence_number",
            name=(
                "uq_research_messages_"
                "conversation_sequence"
            ),
        ),

        # Message Role 只允许以下四种。
        CheckConstraint(
            (
                "role IN "
                "('user', "
                "'assistant', "
                "'system', "
                "'tool')"
            ),
            name="ck_research_messages_role",
        ),

        # 常见读取方式：
        #
        # WHERE conversation_id = ?
        # ORDER BY sequence_number
        Index(
            "ix_research_messages_"
            "conversation_sequence",
            "conversation_id",
            "sequence_number",
        ),
    )


    # ========================================================
    # Identity
    # ========================================================

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )


    conversation_id: Mapped[int] = mapped_column(
        ForeignKey(
            "research_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


    # ========================================================
    # Message Content
    # ========================================================

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )


    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )


    # ========================================================
    # Model Provenance
    # ========================================================

    # User Message 通常为 None。
    #
    # Assistant Message 保存实际使用的模型。
    model_provider: Mapped[
        Optional[str]
    ] = mapped_column(
        String(50),
        nullable=True,
    )


    model_name: Mapped[
        Optional[str]
    ] = mapped_column(
        String(255),
        nullable=True,
    )


    # ========================================================
    # Prompt Provenance
    # ========================================================

    # Day32：
    #
    # 对 Assistant Message 保存主要 User Prompt：
    #
    # rag.answer.user
    #
    # 完整 System/User Prompt 组合同时保存到
    # retrieval_metadata["prompt"]。
    prompt_id: Mapped[
        Optional[str]
    ] = mapped_column(
        String(100),
        nullable=True,
    )


    prompt_version: Mapped[
        Optional[int]
    ] = mapped_column(
        Integer,
        nullable=True,
    )


    # ========================================================
    # Citation Metadata
    # ========================================================

    # Example:
    #
    # [
    #     {
    #         "source_id": "S1",
    #         "chunk_id": 18,
    #         "chunk_index": 17,
    #         "start_page": 6,
    #         "end_page": 7
    #     }
    # ]
    citations: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text(
            "'[]'::jsonb"
        ),
    )


    # ========================================================
    # Retrieval Metadata
    # ========================================================

    # Example:
    #
    # {
    #     "grounded": true,
    #     "retrieval_count": 5,
    #     "invalid_citations": [],
    #     "prompt": {
    #         "system_prompt_id": "...",
    #         "system_prompt_version": 2,
    #         "user_prompt_id": "...",
    #         "user_prompt_version": 1
    #     }
    # }
    retrieval_metadata: Mapped[
        dict
    ] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text(
            "'{}'::jsonb"
        ),
    )


    # ========================================================
    # Time
    # ========================================================

    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


    # ========================================================
    # Relationships
    # ========================================================

    conversation: Mapped[
        "ResearchConversation"
    ] = relationship(
        back_populates="messages",
    )