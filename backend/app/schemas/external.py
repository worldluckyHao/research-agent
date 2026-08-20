from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ============================================================
# Crossref
# ============================================================

class CrossrefPaperResponse(BaseModel):
    """
    标准化后的 Crossref Paper。
    """

    doi: Optional[str] = None

    title: str

    authors: list[str]

    year: Optional[int] = None

    publisher: Optional[str] = None

    container_title: Optional[str] = None

    url: Optional[str] = None

    type: Optional[str] = None

    source: str = "crossref"


# ============================================================
# arXiv
# ============================================================

class ArxivPaperResponse(BaseModel):
    """
    标准化后的 arXiv Paper。
    """

    arxiv_id: str

    title: str

    authors: list[str]

    abstract: str

    year: Optional[int] = None

    published_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None

    categories: list[str]

    primary_category: Optional[str] = None

    doi: Optional[str] = None

    journal_reference: Optional[str] = None

    comment: Optional[str] = None

    abstract_url: Optional[str] = None

    pdf_url: Optional[str] = None

    source: str = "arxiv"


class ArxivSearchResponse(BaseModel):
    """
    arXiv 搜索分页结果。
    """

    items: list[ArxivPaperResponse]

    total: int

    page: int

    page_size: int

    pages: int