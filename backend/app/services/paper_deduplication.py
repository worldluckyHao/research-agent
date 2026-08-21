import re
import unicodedata
from difflib import SequenceMatcher
from typing import Optional

from backend.app.schemas.external import (
    UnifiedPaperMetadata,
)


# 模糊标题判断阈值。
TITLE_SIMILARITY_THRESHOLD = 0.93

# 作者集合 Jaccard 相似度阈值。
AUTHOR_OVERLAP_THRESHOLD = 0.50


def normalize_doi(
    doi: Optional[str],
) -> Optional[str]:
    """
    DOI Canonicalization。

    输入可能是：

    10.1000/xyz
    https://doi.org/10.1000/xyz
    doi:10.1000/xyz

    统一：
    10.1000/xyz
    """

    if not doi:
        return None

    value = (
        doi.strip()
        .lower()
    )


    prefixes = [
        "https://doi.org/",
        "http://doi.org/",
        "doi:",
    ]


    for prefix in prefixes:
        if value.startswith(prefix):
            value = value[
                len(prefix):
            ]


    return value or None


def normalize_arxiv_id(
    arxiv_id: Optional[str],
) -> Optional[str]:
    """
    arXiv ID Canonicalization。

    1706.03762v7
    ↓
    1706.03762
    """

    if not arxiv_id:
        return None

    value = arxiv_id.strip().lower()

    value = re.sub(
        r"v\d+$",
        "",
        value,
    )

    return value or None


def normalize_title(
    title: str,
) -> str:
    """
    Title Normalization。

    处理：
    - 大小写
    - Unicode
    - 标点
    - 多余空格
    """

    value = unicodedata.normalize(
        "NFKC",
        title,
    )

    value = value.lower()

    # 将非字母数字字符转换成空格。
    value = re.sub(
        r"[^\w\s]",
        " ",
        value,
        flags=re.UNICODE,
    )

    value = " ".join(
        value.split()
    )

    return value


def normalize_author(
    author: str,
) -> str:
    """
    作者姓名做轻量标准化。
    """

    value = unicodedata.normalize(
        "NFKC",
        author,
    )

    value = value.lower()

    value = re.sub(
        r"[^\w\s]",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


def calculate_author_overlap(
    authors_a: list[str],
    authors_b: list[str],
) -> float:
    """
    Jaccard Similarity：

              |A ∩ B|
    J(A,B) = ---------
              |A ∪ B|
    """

    set_a = {
        normalize_author(author)
        for author in authors_a
        if author.strip()
    }

    set_b = {
        normalize_author(author)
        for author in authors_b
        if author.strip()
    }


    if not set_a or not set_b:
        return 0.0


    intersection = (
        set_a & set_b
    )

    union = (
        set_a | set_b
    )


    return (
        len(intersection)
        / len(union)
    )


def calculate_title_similarity(
    title_a: str,
    title_b: str,
) -> float:
    """
    使用 Python 标准库 SequenceMatcher
    计算标题相似度。

    范围：
    0.0 ~ 1.0
    """

    normalized_a = normalize_title(
        title_a
    )

    normalized_b = normalize_title(
        title_b
    )


    if not normalized_a or not normalized_b:
        return 0.0


    return SequenceMatcher(
        None,
        normalized_a,
        normalized_b,
    ).ratio()


def _year_compatible(
    year_a: Optional[int],
    year_b: Optional[int],
) -> bool:
    """
    年份允许 ±1。

    原因：
    arXiv 预印本年份和正式发表年份
    可能相差一年。
    """

    if year_a is None or year_b is None:
        return True

    return abs(
        year_a - year_b
    ) <= 1


def are_same_paper(
    paper_a: UnifiedPaperMetadata,
    paper_b: UnifiedPaperMetadata,
) -> bool:
    """
    分层实体匹配策略。

    优先使用强 Identifier，
    Identifier 不足时才使用 Metadata。
    """

    doi_a = normalize_doi(
        paper_a.doi
    )

    doi_b = normalize_doi(
        paper_b.doi
    )


    # --------------------------------------------------------
    # Tier 1：DOI exact match
    # --------------------------------------------------------

    if doi_a and doi_b:
        return doi_a == doi_b


    arxiv_a = normalize_arxiv_id(
        paper_a.arxiv_id
    )

    arxiv_b = normalize_arxiv_id(
        paper_b.arxiv_id
    )


    # --------------------------------------------------------
    # Tier 2：arXiv ID exact match
    # --------------------------------------------------------

    if arxiv_a and arxiv_b:
        return arxiv_a == arxiv_b


    # --------------------------------------------------------
    # Tier 3：Metadata Similarity
    # --------------------------------------------------------

    title_similarity = (
        calculate_title_similarity(
            paper_a.title,
            paper_b.title,
        )
    )


    if (
        title_similarity
        < TITLE_SIMILARITY_THRESHOLD
    ):
        return False


    if not _year_compatible(
        paper_a.year,
        paper_b.year,
    ):
        return False


    author_overlap = (
        calculate_author_overlap(
            paper_a.authors,
            paper_b.authors,
        )
    )


    return (
        author_overlap
        >= AUTHOR_OVERLAP_THRESHOLD
    )

def _prefer_longer_text(
    value_a: Optional[str],
    value_b: Optional[str],
) -> Optional[str]:
    """
    对 abstract 等文本字段，
    优先保留更完整的值。
    """

    if not value_a:
        return value_b

    if not value_b:
        return value_a

    if len(value_b) > len(value_a):
        return value_b

    return value_a


def _merge_unique_strings(
    values_a: list[str],
    values_b: list[str],
) -> list[str]:
    """
    合并字符串列表并保持原始顺序。
    """

    result = []

    seen = set()

    for value in (
        values_a + values_b
    ):
        key = value.strip().lower()

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


def merge_papers(
    primary: UnifiedPaperMetadata,
    secondary: UnifiedPaperMetadata,
) -> UnifiedPaperMetadata:
    """
    将两个已确认属于同一论文的记录融合。

    原则：
    - Identifier 尽量补齐；
    - Abstract 取更完整值；
    - Citation 取最大值；
    - OA 只要一个来源确认 True 就为 True；
    - Sources/Provider IDs 全部保留。
    """

    sources = _merge_unique_strings(
        primary.sources
        or [primary.provider],

        secondary.sources
        or [secondary.provider],
    )


    provider_ids = {
        **primary.provider_ids,
        **secondary.provider_ids,
    }


    # DOI Canonicalization。
    doi = (
        normalize_doi(primary.doi)
        or normalize_doi(secondary.doi)
    )


    arxiv_id = (
        normalize_arxiv_id(
            primary.arxiv_id
        )
        or normalize_arxiv_id(
            secondary.arxiv_id
        )
    )


    authors = (
        primary.authors
        if len(primary.authors)
        >= len(secondary.authors)
        else secondary.authors
    )


    topics = _merge_unique_strings(
        primary.topics,
        secondary.topics,
    )


    # 如果任何来源明确确认 OA，
    # 则认为该论文有 Open Access 版本。
    if (
        primary.is_open_access is True
        or secondary.is_open_access is True
    ):
        is_open_access = True

    elif (
        primary.is_open_access is False
        and secondary.is_open_access is False
    ):
        is_open_access = False

    else:
        is_open_access = (
            primary.is_open_access
            if primary.is_open_access
            is not None
            else secondary.is_open_access
        )


    return UnifiedPaperMetadata(
        # 保留 primary 作为主要 Provider。
        provider=primary.provider,

        provider_id=primary.provider_id,

        sources=sources,

        provider_ids=provider_ids,

        # 一般保留较完整标题。
        title=(
            primary.title
            if len(primary.title)
            >= len(secondary.title)
            else secondary.title
        ),

        authors=authors,

        abstract=_prefer_longer_text(
            primary.abstract,
            secondary.abstract,
        ),

        year=(
            primary.year
            or secondary.year
        ),

        publication_date=(
            primary.publication_date
            or secondary.publication_date
        ),

        doi=doi,

        arxiv_id=arxiv_id,

        url=(
            primary.url
            or secondary.url
        ),

        pdf_url=(
            primary.pdf_url
            or secondary.pdf_url
        ),

        venue=(
            primary.venue
            or secondary.venue
        ),

        cited_by_count=max(
            primary.cited_by_count,
            secondary.cited_by_count,
        ),

        is_open_access=is_open_access,

        language=(
            primary.language
            or secondary.language
        ),

        topics=topics,
    )

def deduplicate_and_merge(
    papers: list[UnifiedPaperMetadata],
) -> list[UnifiedPaperMetadata]:
    """
    对多 Provider Paper Candidates
    进行实体解析与元数据融合。

    当前数据规模主要针对交互式搜索，
    因此使用 O(n²) 两两匹配。

    后续大规模离线导入时，
    可以先按 DOI / arXiv ID / Title Hash
    blocking，再减少比较次数。
    """

    unique_papers: list[
        UnifiedPaperMetadata
    ] = []


    for candidate in papers:

        matched_index = None


        for index, existing in enumerate(
            unique_papers
        ):
            if are_same_paper(
                candidate,
                existing,
            ):
                matched_index = index
                break


        # 没有重复记录。
        if matched_index is None:
            unique_papers.append(
                candidate
            )

            continue


        # 已经找到对应实体：
        # 做 Metadata Fusion。
        unique_papers[
            matched_index
        ] = merge_papers(
            unique_papers[
                matched_index
            ],
            candidate,
        )


    return unique_papers