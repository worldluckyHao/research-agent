from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
)
from typing import Optional

class PaperDocumentResponse(BaseModel):
    """
    对客户端暴露的 Document Metadata。

    注意：
    不返回 storage_key，
    避免泄露内部 Storage 实现。
    """

    model_config = ConfigDict(
        from_attributes=True,
    )


    id: int

    paper_id: int

    uploaded_by_id: int | None

    original_filename: str

    storage_backend: str

    mime_type: str

    size_bytes: int

    sha256: str

    status: str

    created_at: datetime

    updated_at: datetime

    page_count: Optional[int] = None

    parser_name: Optional[str] = None

    parser_version: Optional[str] = None

    parse_error: Optional[str] = None

    parsed_at: Optional[datetime] = None

    chunk_status: str

    chunk_count: int

    chunker_name: Optional[str] = None

    chunker_version: Optional[str] = None

    chunk_size_tokens: Optional[int] = None

    chunk_overlap_tokens: Optional[int] = None

    chunk_error: Optional[str] = None

    chunked_at: Optional[datetime] = None

    embedding_status: str

    embedding_count: int

    embedding_provider: Optional[str] = None

    embedding_model: Optional[str] = None

    embedding_dimension: Optional[int] = None

    embedding_normalized: Optional[bool] = None

    embedding_error: Optional[str] = None

    embedded_at: Optional[datetime] = None


class PaperDocumentListResponse(BaseModel):
    """
    Paper 的 Document 列表。
    """

    items: list[PaperDocumentResponse]

    total: int

class PaperDocumentPageResponse(
    BaseModel
):
    """
    PDF 单页解析文本。
    """

    model_config = ConfigDict(
        from_attributes=True,
    )


    id: int

    document_id: int

    page_number: int

    text: str

    char_count: int


class PaperDocumentPageListResponse(
    BaseModel
):
    """
    PDF Page 分页响应。
    """

    items: list[
        PaperDocumentPageResponse
    ]

    total: int

    page: int

    page_size: int

class PaperDocumentChunkResponse(
    BaseModel
):
    """
    Document Chunk Response。
    """

    model_config = ConfigDict(
        from_attributes=True,
    )


    id: int

    document_id: int

    chunk_index: int

    content: str

    start_page: int

    end_page: int

    token_count: int

    char_count: int

    content_sha256: str


class PaperDocumentChunkListResponse(
    BaseModel
):
    """
    Chunk 分页结果。
    """

    items: list[
        PaperDocumentChunkResponse
    ]

    total: int

    page: int

    page_size: int