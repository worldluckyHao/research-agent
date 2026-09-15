from pydantic import (
    BaseModel,
    Field,
)


class EmbeddingModelInfoResponse(
    BaseModel
):
    """
    当前 Embedding Model 信息。
    """

    provider: str

    model_name: str

    dimension: int

    normalized: bool

    device: str


class ChunkEmbeddingPreviewItem(
    BaseModel
):
    """
    Chunk Embedding Preview。

    不返回完整 384 维向量，
    只返回前几个数供开发验证。
    """

    chunk_id: int

    chunk_index: int

    start_page: int

    end_page: int

    token_count: int

    vector_dimension: int

    vector_norm: float

    vector_preview: list[
        float
    ] = Field(
        default_factory=list
    )


class DocumentEmbeddingPreviewResponse(
    BaseModel
):
    """
    Document Embedding Preview Response。
    """

    document_id: int

    chunk_count: int

    preview_count: int

    model: EmbeddingModelInfoResponse

    items: list[
        ChunkEmbeddingPreviewItem
    ]


from datetime import datetime
from typing import Optional


class ChunkEmbeddingMetadataResponse(
    BaseModel
):
    """
    一个 Chunk 已持久化的
    Embedding Metadata。

    不返回完整 Vector。
    """

    id: int

    chunk_id: int

    chunk_index: int

    start_page: int

    end_page: int

    provider: str

    model_name: str

    dimension: int

    normalized: bool

    content_sha256: str

    created_at: datetime


class DocumentEmbeddingListResponse(
    BaseModel
):
    """
    Document Embedding 列表。
    """

    document_id: int

    total: int

    page: int

    page_size: int

    items: list[
        ChunkEmbeddingMetadataResponse
    ]