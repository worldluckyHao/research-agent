from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.app.core.config import settings
from backend.app.db.base import Base


class PaperDocumentChunkEmbedding(Base):
    """
    Chunk 的向量表示。

    Chunk 与 Embedding 分表，
    为未来多模型、多版本 Embedding
    保留扩展能力。
    """

    __tablename__ = (
        "paper_document_chunk_embeddings"
    )


    __table_args__ = (

        # 当前一个 Chunk 对某个模型
        # 只允许存在一份向量。
        UniqueConstraint(
            "chunk_id",
            "provider",
            "model_name",
            name=(
                "uq_chunk_embeddings_"
                "chunk_provider_model"
            ),
        ),

        Index(
            "ix_chunk_embeddings_"
            "chunk_id",
            "chunk_id",
        ),

        # HNSW Vector Index。
        #
        # 使用 cosine distance。
        Index(
            "ix_chunk_embeddings_"
            "embedding_hnsw",
            "embedding",

            postgresql_using="hnsw",

            postgresql_ops={
                "embedding":
                    "vector_cosine_ops"
            },

            postgresql_with={
                "m":
                    settings.VECTOR_HNSW_M,

                "ef_construction":
                    settings
                    .VECTOR_HNSW_EF_CONSTRUCTION,
            },
        ),
    )


    id: Mapped[int] = mapped_column(
        primary_key=True,
    )


    chunk_id: Mapped[int] = mapped_column(
        ForeignKey(
            "paper_document_chunks.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )


    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )


    model_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


    dimension: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


    normalized: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )


    # 生成 Vector 时对应的 Chunk 内容 Hash。
    #
    # 如果 Chunk 内容变化，
    # 可以判断旧 Vector 已经过期。
    content_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )


    embedding: Mapped[list[float]] = mapped_column(
        Vector(
            settings.EMBEDDING_DIMENSION
        ),
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


    chunk: Mapped[
        "PaperDocumentChunk"
    ] = relationship(
        back_populates="embeddings",
    )