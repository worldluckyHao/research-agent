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