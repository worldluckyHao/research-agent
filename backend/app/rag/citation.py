import re

from backend.app.rag.context import (
    RAGSource,
)


CITATION_PATTERN = re.compile(
    r"\[(S\d+)\]"
)


def extract_citation_ids(
    answer: str,
) -> list[str]:
    """
    从 LLM Answer 中提取：

        [S1]
        [S2]
        ...

    并按照第一次出现顺序去重。
    """

    matches = (
        CITATION_PATTERN
        .findall(
            answer
        )
    )


    seen = set()

    ordered = []


    for source_id in matches:

        if source_id in seen:
            continue


        seen.add(
            source_id
        )

        ordered.append(
            source_id
        )


    return ordered


def resolve_used_sources(
    answer: str,
    available_sources: list[
        RAGSource
    ],
) -> tuple[
    list[RAGSource],
    list[str],
]:
    """
    把 Answer 中的 [Sx]
    映射回真实 Source。

    Returns:
        used_sources
        invalid_source_ids
    """

    citation_ids = (
        extract_citation_ids(
            answer
        )
    )


    source_map = {
        source.source_id:
            source

        for source
        in available_sources
    }


    used_sources = []

    invalid_ids = []


    for source_id in citation_ids:

        source = source_map.get(
            source_id
        )


        if source is None:

            invalid_ids.append(
                source_id
            )

            continue


        used_sources.append(
            source
        )


    return (
        used_sources,
        invalid_ids,
    )