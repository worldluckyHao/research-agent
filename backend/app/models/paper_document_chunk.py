from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
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


class PaperDocumentChunk(Base):
    """
    PDF Chunk。

    Day26 Embedding 会直接基于本表生成向量。
    """

    __tablename__ = (
        "paper_document_chunks"
    )


    __table_args__ = (

        # 一个 Document 中，
        # Chunk Index 唯一。
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name=(
                "uq_document_chunks_"
                "document_index"
            ),
        ),

        Index(
            "ix_document_chunks_"
            "document_index",
            "document_id",
            "chunk_index",
        ),
    )


    id: Mapped[int] = mapped_column(
        primary_key=True,
    )


    document_id: Mapped[int] = mapped_column(
        ForeignKey(
            "paper_documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )


    start_page: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


    end_page: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


    char_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


    content_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )


    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


    document: Mapped[
        "PaperDocument"
    ] = relationship(
        back_populates="chunks",
    )

    embeddings: Mapped[
        list["PaperDocumentChunkEmbedding"]
    ] = relationship(
        back_populates="chunk",

        # Chunk 被删除时，
        # ORM 层同时删除 Embedding。
        cascade="all, delete-orphan",

        lazy="selectin",
    )