from datetime import datetime
from typing import Optional
from xml.etree import ElementTree

from backend.app.core.exceptions import (
    ExternalServiceResponseException,
)


# Atom / OpenSearch / arXiv XML namespaces。
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def _clean_text(
    value: Optional[str],
) -> str:
    """
    清理 arXiv XML 中常见的换行和多余空格。
    """

    if not value:
        return ""

    return " ".join(
        value.split()
    )


def _parse_datetime(
    value: Optional[str],
) -> Optional[datetime]:
    """
    将 arXiv ISO 8601 时间转成 timezone-aware datetime。
    """

    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

    except ValueError:
        return None


def _extract_arxiv_id(
    entry_id: str,
) -> str:
    """
    从：
        http://arxiv.org/abs/1706.03762v7

    提取：
        1706.03762v7
    """

    marker = "/abs/"

    if marker in entry_id:
        return entry_id.split(
            marker,
            maxsplit=1,
        )[1]

    return entry_id


def _find_link(
    entry: ElementTree.Element,
    rel: str,
) -> Optional[str]:
    """
    根据 Atom link 的 rel 查找 URL。
    """

    for link in entry.findall(
        "atom:link",
        NAMESPACES,
    ):
        if link.attrib.get("rel") == rel:
            return link.attrib.get("href")

    return None


def _find_pdf_link(
    entry: ElementTree.Element,
) -> Optional[str]:
    """
    arXiv PDF link 的 title 通常为 pdf。
    """

    for link in entry.findall(
        "atom:link",
        NAMESPACES,
    ):
        if link.attrib.get("title") == "pdf":
            return link.attrib.get("href")

    return None


def _parse_entry(
    entry: ElementTree.Element,
) -> dict:
    """
    将一个 Atom <entry> 转成 Python dict。
    """

    entry_id = _clean_text(
        entry.findtext(
            "atom:id",
            default="",
            namespaces=NAMESPACES,
        )
    )

    title = _clean_text(
        entry.findtext(
            "atom:title",
            default="",
            namespaces=NAMESPACES,
        )
    )

    abstract = _clean_text(
        entry.findtext(
            "atom:summary",
            default="",
            namespaces=NAMESPACES,
        )
    )


    # 一个 entry 可以有多个 author。
    authors = []

    for author in entry.findall(
        "atom:author",
        NAMESPACES,
    ):
        name = _clean_text(
            author.findtext(
                "atom:name",
                default="",
                namespaces=NAMESPACES,
            )
        )

        if name:
            authors.append(name)


    # 一个 Paper 可以属于多个 arXiv category。
    categories = [
        category.attrib["term"]
        for category in entry.findall(
            "atom:category",
            NAMESPACES,
        )
        if category.attrib.get("term")
    ]


    primary_category_element = entry.find(
        "arxiv:primary_category",
        NAMESPACES,
    )

    primary_category = None

    if primary_category_element is not None:
        primary_category = (
            primary_category_element.attrib.get(
                "term"
            )
        )


    published_at = _parse_datetime(
        entry.findtext(
            "atom:published",
            default=None,
            namespaces=NAMESPACES,
        )
    )

    updated_at = _parse_datetime(
        entry.findtext(
            "atom:updated",
            default=None,
            namespaces=NAMESPACES,
        )
    )


    doi = _clean_text(
        entry.findtext(
            "arxiv:doi",
            default="",
            namespaces=NAMESPACES,
        )
    ) or None


    journal_reference = _clean_text(
        entry.findtext(
            "arxiv:journal_ref",
            default="",
            namespaces=NAMESPACES,
        )
    ) or None


    comment = _clean_text(
        entry.findtext(
            "arxiv:comment",
            default="",
            namespaces=NAMESPACES,
        )
    ) or None


    return {
        "arxiv_id": _extract_arxiv_id(
            entry_id
        ),

        "title": title,

        "authors": authors,

        "abstract": abstract,

        "published_at": published_at,

        "updated_at": updated_at,

        "year": (
            published_at.year
            if published_at
            else None
        ),

        "categories": categories,

        "primary_category": primary_category,

        "doi": doi,

        "journal_reference": journal_reference,

        "comment": comment,

        # alternate 一般对应 abstract 页面。
        "abstract_url": _find_link(
            entry,
            rel="alternate",
        ),

        "pdf_url": _find_pdf_link(
            entry
        ),

        "source": "arxiv",
    }


def parse_arxiv_feed(
    xml_text: str,
) -> dict:
    """
    解析完整 arXiv Atom Feed。

    返回：
    {
        "total": ...,
        "items": [...]
    }
    """

    try:
        root = ElementTree.fromstring(
            xml_text
        )

    except ElementTree.ParseError as exc:
        raise ExternalServiceResponseException() from exc


    total_text = root.findtext(
        "opensearch:totalResults",
        default="0",
        namespaces=NAMESPACES,
    )

    try:
        total = int(
            total_text
        )
    except ValueError:
        total = 0


    entries = root.findall(
        "atom:entry",
        NAMESPACES,
    )


    items = [
        _parse_entry(entry)
        for entry in entries
    ]


    return {
        "total": total,
        "items": items,
    }