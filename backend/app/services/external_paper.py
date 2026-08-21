import httpx
import asyncio
import logging
from backend.app.services.paper_deduplication import (
    deduplicate_and_merge,
)
from backend.app.schemas.external import (
    MultiSourcePaperSearchResponse,
)
from backend.app.clients.crossref import (
    CrossrefClient,
)
from typing import Literal

from backend.app.clients.arxiv import ArxivClient
from backend.app.core.exceptions import (
    ExternalResourceNotFoundException,
)
from backend.app.parsers.arxiv import (
    parse_arxiv_feed,
)
from backend.app.schemas.external import (
    ArxivPaperResponse,
    ArxivSearchResponse,
    CrossrefPaperResponse,
)
from backend.app.providers.base import (
    PaperProvider,
)

from backend.app.schemas.external import (
    PaperSearchSort,
    UnifiedPaperMetadata,
    UnifiedPaperSearchResponse,
)

def _extract_authors(
    work: dict,
) -> list[str]:
    """
    将 Crossref author 对象转换成姓名字符串。
    """

    authors = []

    for author in work.get("author", []):
        given = author.get("given", "")
        family = author.get("family", "")

        full_name = (
            f"{given} {family}"
        ).strip()

        if full_name:
            authors.append(full_name)

    return authors


def _extract_year(
    work: dict,
) -> int | None:
    """
    从 Crossref 日期字段中提取年份。
    """

    # 优先 published，其次 issued。
    date_data = (
        work.get("published")
        or work.get("issued")
    )

    if not isinstance(date_data, dict):
        return None

    date_parts = date_data.get(
        "date-parts",
        []
    )

    if (
        not date_parts
        or not date_parts[0]
    ):
        return None

    year = date_parts[0][0]

    if isinstance(year, int):
        return year

    return None


async def get_crossref_paper(
    client: httpx.AsyncClient,
    doi: str,
) -> CrossrefPaperResponse:
    """
    查询 Crossref，并转换为 Research Agent 统一结构。
    """

    crossref_client = CrossrefClient(
        client=client
    )

    work = await crossref_client.get_work_by_doi(
        doi=doi
    )


    # Crossref title 通常为 list。
    titles = work.get(
        "title",
        []
    )

    title = (
        titles[0]
        if titles
        else "Untitled"
    )


    container_titles = work.get(
        "container-title",
        []
    )

    container_title = (
        container_titles[0]
        if container_titles
        else None
    )


    return CrossrefPaperResponse(
        doi=work.get("DOI"),

        title=title,

        authors=_extract_authors(
            work
        ),

        year=_extract_year(
            work
        ),

        publisher=work.get(
            "publisher"
        ),

        container_title=container_title,

        url=work.get(
            "URL"
        ),

        type=work.get(
            "type"
        ),

        source="crossref",
    )

# ============================================================
# arXiv Search
# ============================================================

ARXIV_FIELD_MAP = {
    "all": "all",
    "title": "ti",
    "abstract": "abs",
    "author": "au",
}


def _build_arxiv_search_query(
    query: str,
    field: str,
    category: str | None = None,
) -> str:
    """
    将 Research Agent 查询参数转换成 arXiv search_query。

    例如：

    query="precipitation forecasting"
    field="title"

    ↓

    ti:"precipitation forecasting"
    """

    # 把用户输入当作普通搜索文本，
    # 不直接允许其构造完整 arXiv 查询语法。
    normalized_query = " ".join(
        query.replace(
            '"',
            " ",
        ).split()
    )

    prefix = ARXIV_FIELD_MAP[
        field
    ]

    search_query = (
        f'{prefix}:"{normalized_query}"'
    )


    # 可选 category 过滤。
    if category:
        normalized_category = (
            category.strip()
        )

        search_query += (
            f" AND cat:{normalized_category}"
        )


    return search_query

async def search_arxiv_papers(
    arxiv_client: ArxivClient,
    query: str,
    field: Literal[
        "all",
        "title",
        "abstract",
        "author",
    ],
    category: str | None,
    page: int,
    page_size: int,
    sort_by: Literal[
        "relevance",
        "lastUpdatedDate",
        "submittedDate",
    ],
    sort_order: Literal[
        "ascending",
        "descending",
    ],
) -> ArxivSearchResponse:
    """
    搜索 arXiv 论文，并转换成 Research Agent 的 JSON 结构。
    """

    search_query = (
        _build_arxiv_search_query(
            query=query,
            field=field,
            category=category,
        )
    )


    # Research Agent page → arXiv start。
    start = (
        page - 1
    ) * page_size


    xml_text = await arxiv_client.search(
        search_query=search_query,
        start=start,
        max_results=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


    parsed = parse_arxiv_feed(
        xml_text
    )


    total = parsed["total"]

    pages = (
        (total + page_size - 1)
        // page_size
        if total > 0
        else 0
    )


    items = [
        ArxivPaperResponse(
            **item
        )
        for item in parsed["items"]
    ]


    return ArxivSearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

async def get_arxiv_paper_by_id(
    arxiv_client: ArxivClient,
    arxiv_id: str,
) -> ArxivPaperResponse:
    """
    根据 arXiv ID 精确查询论文。
    """

    xml_text = await arxiv_client.get_by_id(
        arxiv_id=arxiv_id.strip()
    )


    parsed = parse_arxiv_feed(
        xml_text
    )


    if not parsed["items"]:
        raise ExternalResourceNotFoundException()


    return ArxivPaperResponse(
        **parsed["items"][0]
    )

# ============================================================
# Unified Paper Provider Service
# ============================================================

async def search_papers(
    provider: PaperProvider,
    query: str,
    page: int,
    page_size: int,
    sort: PaperSearchSort,
) -> UnifiedPaperSearchResponse:
    """
    使用统一 PaperProvider 搜索论文。

    今天这里只接 OpenAlex。
    Day19 后可以进一步扩展成多 Provider 聚合。
    """

    return await provider.search(
        query=query,
        page=page,
        page_size=page_size,
        sort=sort,
    )


async def get_paper_from_provider(
    provider: PaperProvider,
    identifier: str,
) -> UnifiedPaperMetadata:
    """
    使用统一 Provider 获取单篇论文。
    """

    return await provider.get(
        identifier=identifier
    )

async def search_multiple_providers(
    provider_map: dict[str, PaperProvider],
    selected_providers: list[str],
    query: str,
    limit: int,
    sort: PaperSearchSort,
) -> MultiSourcePaperSearchResponse:
    """
    并发搜索多个论文 Provider。

    设计目标：
    1. Provider 并行请求；
    2. 单一 Provider 失败时 Graceful Degradation；
    3. 合并 Candidates；
    4. Deduplicate；
    5. Metadata Fusion。
    """

    providers = [
        provider_map[name]
        for name in selected_providers
    ]


    # --------------------------------------------------------
    # 并发 Fan-out
    # --------------------------------------------------------

    tasks = [
        provider.search(
            query=query,
            page=1,
            page_size=limit,
            sort=sort,
        )
        for provider in providers
    ]


    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )


    successful_results = []

    failed_providers = []


    # --------------------------------------------------------
    # Graceful Degradation
    # --------------------------------------------------------

    for provider, result in zip(
        providers,
        results,
    ):
        if isinstance(
            result,
            Exception,
        ):
            failed_providers.append(
                provider.name
            )

            logging.warning(
                "Paper provider failed: "
                "provider=%s error=%s",
                provider.name,
                type(result).__name__,
            )

            continue


        successful_results.append(
            result
        )


    # 所有 Provider 都失败，
    # 此时不能假装返回空搜索结果。
    if not successful_results:
        from backend.app.core.exceptions import (
            ExternalServiceUnavailableException,
        )

        raise ExternalServiceUnavailableException()


    # --------------------------------------------------------
    # Fair Candidate Interleaving
    # --------------------------------------------------------

    candidate_lists = [
        result.items
        for result
        in successful_results
    ]


    candidates = []

    max_length = max(
        len(items)
        for items in candidate_lists
    )


    # 轮询各 Provider 的排名结果：
    #
    # OpenAlex #1
    # arXiv #1
    # Crossref #1
    # OpenAlex #2
    # ...
    #
    # 避免固定 Provider 永远排在前面。
    for index in range(max_length):

        for items in candidate_lists:

            if index < len(items):
                candidates.append(
                    items[index]
                )


    # --------------------------------------------------------
    # Entity Resolution + Metadata Fusion
    # --------------------------------------------------------

    unique_papers = (
        deduplicate_and_merge(
            candidates
        )
    )


    # --------------------------------------------------------
    # Unified Ranking
    # --------------------------------------------------------

    if sort == PaperSearchSort.CITED:

        unique_papers.sort(
            key=lambda paper: (
                paper.cited_by_count
            ),
            reverse=True,
        )


    elif sort == PaperSearchSort.NEWEST:

        unique_papers.sort(
            key=lambda paper: (
                paper.publication_date
                or paper.year
                or 0
            ),
            reverse=True,
        )


    # relevance 保留 Provider
    # interleaving 后的整体顺序。


    return MultiSourcePaperSearchResponse(
        query=query,

        providers=[
            result.provider
            for result
            in successful_results
        ],

        failed_providers=(
            failed_providers
        ),

        candidate_count=len(
            candidates
        ),

        unique_count=len(
            unique_papers
        ),

        items=unique_papers[
            :limit
        ],
    )