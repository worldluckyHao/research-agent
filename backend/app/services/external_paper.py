import httpx

from backend.app.clients.crossref import (
    CrossrefClient,
)
from backend.app.schemas.external import (
    CrossrefPaperResponse,
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