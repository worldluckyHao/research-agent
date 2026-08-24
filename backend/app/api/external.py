from typing import (
    List,
    Literal,
)
import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Path,
    Query,
    status,
)

from backend.app.clients.arxiv import (
    ArxivClient,
)
from backend.app.core.config import settings
from backend.app.dependencies import (
    get_arxiv_client,
    get_arxiv_provider,
    get_crossref_provider,
    get_current_user,
    get_db,
    get_http_client,
    get_openalex_provider,
    get_redis,
)
from backend.app.schemas.external import (
    ArxivPaperResponse,
    ArxivSearchResponse,
    CrossrefPaperResponse,
)
from backend.app.services import (
    external_paper,
)
from backend.app.providers.arxiv import (
    ArxivProvider,
)
from backend.app.providers.crossref import (
    CrossrefProvider,
)
from backend.app.providers.openalex import (
    OpenAlexProvider,
)

from backend.app.schemas.external import (
    PaperSearchSort,
    UnifiedPaperMetadata,
    UnifiedPaperSearchResponse,
    MultiSourcePaperSearchResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import (
    get_current_user,
    get_db,
)
from backend.app.models.user import User
from backend.app.schemas.external import (
    PaperImportJobResponse,
    PaperImportRequest,
)
from backend.app.services import (
    paper_import,
)
import redis.asyncio as redis

from backend.app.services.cache_service import CacheService

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

# ============================================================
# OpenAlex Search
# ============================================================

@router.get(
    "/openalex/search",
    response_model=UnifiedPaperSearchResponse,
)
async def search_openalex(
    query: str = Query(
        min_length=2,
        max_length=300,
        description="Paper search keywords",
    ),

    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=10,
        ge=1,
        le=settings.OPENALEX_MAX_PAGE_SIZE,
    ),

    sort: PaperSearchSort = Query(
        default=PaperSearchSort.RELEVANCE,
    ),

    provider: OpenAlexProvider = Depends(
        get_openalex_provider
    ),
):
    """
    使用 OpenAlex 搜索论文，
    返回 Research Agent 统一论文格式。
    """

    return await external_paper.search_papers(
        provider=provider,
        query=query,
        page=page,
        page_size=page_size,
        sort=sort,
    )

@router.get(
    "/openalex/works/{identifier:path}",
    response_model=UnifiedPaperMetadata,
)
async def get_openalex_work(
    identifier: str = Path(
        min_length=2,
        max_length=255,
    ),

    provider: OpenAlexProvider = Depends(
        get_openalex_provider
    ),
):
    """
    根据 OpenAlex ID 或 DOI 查询论文。

    示例：
    W2741809807

    或：
    doi:10.xxxx/xxxx
    """

    return await external_paper.get_paper_from_provider(
        provider=provider,
        identifier=identifier,
    )

# ============================================================
# Multi-Source Unified Paper Search
# ============================================================

@router.get(
    "/papers/search",
    response_model=MultiSourcePaperSearchResponse,
)
async def search_papers_multi_source(
    query: str = Query(
        min_length=2,
        max_length=300,
        description=(
            "Paper search keywords"
        ),
    ),

    providers: List[
        Literal[
            "openalex",
            "arxiv",
            "crossref",
        ]
    ] = Query(
        default=[
            "openalex",
            "arxiv",
            "crossref",
        ],
        description=(
            "Providers to search"
        ),
    ),

    limit: int = Query(
        default=10,
        ge=1,
        le=20,
    ),

    sort: PaperSearchSort = Query(
        default=PaperSearchSort.RELEVANCE,
    ),

    openalex_provider: OpenAlexProvider = Depends(
        get_openalex_provider
    ),

    arxiv_provider: ArxivProvider = Depends(
        get_arxiv_provider
    ),

    crossref_provider: CrossrefProvider = Depends(
        get_crossref_provider
    ),
    redis_client: redis.Redis = Depends(
        get_redis
    ),
):
    """
    多数据源统一论文搜索。

    流程：

    OpenAlex / arXiv / Crossref
                ↓
           Concurrent Search
                ↓
          Unified Metadata
                ↓
             Dedup
                ↓
          Metadata Fusion
    """

    # 去掉重复 Provider 参数。
    selected_providers = list(
        dict.fromkeys(
            providers
        )
    )


    provider_map = {
        "openalex": openalex_provider,
        "arxiv": arxiv_provider,
        "crossref": crossref_provider,
    }

    cache_service = CacheService(
        redis_client=redis_client
    )

    return await external_paper.search_multiple_providers_cached(
        cache_service=cache_service,
        provider_map=provider_map,
        selected_providers=selected_providers,
        query=query,
        limit=limit,
        sort=sort,
    )

# ============================================================
# Paper Import Jobs
# ============================================================

@router.post(
    "/papers/import-jobs",
    response_model=PaperImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_paper_import_job(
    request_data: PaperImportRequest,

    background_tasks: BackgroundTasks,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    创建论文导入 Job。

    API 立即返回 202，
    实际数据库导入由 BackgroundTasks 执行。
    """

    # 如果要求加入 Project，
    # 在返回 202 前先检查权限。
    if request_data.project_id is not None:

        from backend.app.services import (
            research_project,
        )

        await research_project.get_owned_project(
            db=db,
            project_id=request_data.project_id,
            user_id=current_user.id,
        )


    # 先把 Job 保存到 PostgreSQL。
    job = await paper_import.create_import_job(
        db=db,
        user_id=current_user.id,
        request_data=request_data,
    )


    # Response 返回之后执行。
    background_tasks.add_task(
        paper_import.run_paper_import_job,
        job.id,
    )


    return job

@router.get(
    "/papers/import-jobs/{job_id}",
    response_model=PaperImportJobResponse,
)
async def get_paper_import_job(
    job_id: str,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    查询当前用户自己的 Import Job。
    """

    return await paper_import.get_import_job(
        db=db,
        job_id=job_id,
        user_id=current_user.id,
    )