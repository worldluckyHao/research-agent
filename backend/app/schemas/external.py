from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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

# ============================================================
# Unified Paper Metadata
# ============================================================

class PaperSearchSort(str, Enum):
    """
    Research Agent 自己定义的统一排序方式。

    不直接暴露第三方 API 的 sort 参数，
    防止上层业务依赖 Provider 私有语法。
    """

    RELEVANCE = "relevance"
    NEWEST = "newest"
    CITED = "cited"


class UnifiedPaperMetadata(BaseModel):
    """
    Research Agent 内部统一论文元数据。

    provider/provider_id：
        当前主要数据源及其 ID。

    sources/provider_ids：
        记录该论文实际上由哪些数据源共同贡献，
        为 Day19 Metadata Fusion 提供数据来源追踪。
    """

    provider: str

    provider_id: str

    # Day19：论文可能来自多个 Provider。
    sources: list[str] = Field(
        default_factory=list
    )

    # 例如：
    # {
    #     "openalex": "W123",
    #     "arxiv": "1706.03762"
    # }
    provider_ids: dict[str, str] = Field(
        default_factory=dict
    )

    title: str

    authors: list[str] = Field(
        default_factory=list
    )

    abstract: Optional[str] = None

    year: Optional[int] = None

    publication_date: Optional[date] = None

    doi: Optional[str] = None

    arxiv_id: Optional[str] = None

    url: Optional[str] = None

    pdf_url: Optional[str] = None

    venue: Optional[str] = None

    cited_by_count: int = 0

    is_open_access: Optional[bool] = None

    language: Optional[str] = None

    topics: list[str] = Field(
        default_factory=list
    )


class UnifiedPaperSearchResponse(BaseModel):
    """
    统一论文搜索响应。
    """

    provider: str

    items: list[UnifiedPaperMetadata]

    total: int

    page: int

    page_size: int

    pages: int

class MultiSourcePaperSearchResponse(BaseModel):
    """
    多数据源论文搜索结果。

    注意：
    多个 Provider 的 total 无法简单相加，
    因为 Provider 之间存在重复论文。

    因此这里不伪造 total_pages，
    而是暴露真实候选数和去重后的唯一论文数。
    """

    query: str

    providers: list[str]

    failed_providers: list[str] = Field(
        default_factory=list
    )

    candidate_count: int

    unique_count: int

    items: list[UnifiedPaperMetadata]