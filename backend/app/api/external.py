from typing import Literal

import httpx
from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
)

from backend.app.clients.arxiv import (
    ArxivClient,
)
from backend.app.core.config import settings
from backend.app.dependencies import (
    get_arxiv_client,
    get_http_client,
)
from backend.app.schemas.external import (
    ArxivPaperResponse,
    ArxivSearchResponse,
    CrossrefPaperResponse,
)
from backend.app.services import (
    external_paper,
)


router = APIRouter(
    prefix="/external",
    tags=["external"],
)


# ============================================================
# Crossref
# ============================================================

@router.get(
    "/crossref/works/{doi:path}",
    response_model=CrossrefPaperResponse,
)
async def get_crossref_work(
    doi: str = Path(
        min_length=3,
        max_length=255,
    ),

    client: httpx.AsyncClient = Depends(
        get_http_client
    ),
):
    """
    根据 DOI 查询 Crossref 学术元数据。
    """

    return await external_paper.get_crossref_paper(
        client=client,
        doi=doi,
    )


# ============================================================
# arXiv Search
# ============================================================

@router.get(
    "/arxiv/search",
    response_model=ArxivSearchResponse,
)
async def search_arxiv(
    # 用户自然语言关键词。
    query: str = Query(
        min_length=2,
        max_length=200,
        description="Search keywords",
    ),

    # 搜索字段。
    field: Literal[
        "all",
        "title",
        "abstract",
        "author",
    ] = "all",

    # 例如：
    # cs.LG
    # cs.AI
    # physics.ao-ph
    category: str | None = Query(
        default=None,
        max_length=50,
    ),

    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=10,
        ge=1,
        le=settings.ARXIV_MAX_PAGE_SIZE,
    ),

    sort_by: Literal[
        "relevance",
        "lastUpdatedDate",
        "submittedDate",
    ] = "relevance",

    sort_order: Literal[
        "ascending",
        "descending",
    ] = "descending",

    arxiv_client: ArxivClient = Depends(
        get_arxiv_client
    ),
):
    """
    搜索 arXiv Papers。

    支持：
    - 关键词
    - 搜索字段
    - category
    - 分页
    - 排序
    """

    return await external_paper.search_arxiv_papers(
        arxiv_client=arxiv_client,
        query=query,
        field=field,
        category=category,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# ============================================================
# arXiv ID Lookup
# ============================================================

@router.get(
    "/arxiv/papers/{arxiv_id:path}",
    response_model=ArxivPaperResponse,
)
async def get_arxiv_paper(
    arxiv_id: str = Path(
        min_length=3,
        max_length=100,
    ),

    arxiv_client: ArxivClient = Depends(
        get_arxiv_client
    ),
):
    """
    根据 arXiv ID 查询单篇论文。
    """

    return await external_paper.get_arxiv_paper_by_id(
        arxiv_client=arxiv_client,
        arxiv_id=arxiv_id,
    )