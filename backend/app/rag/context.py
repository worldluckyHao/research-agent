from dataclasses import dataclass

from backend.app.retrieval.base import (
    RetrievalCandidate,
)


@dataclass(frozen=True)
class RAGSource:
    """
    RAG 使用的一条 Evidence Source。
    """

    source_id: str

    chunk_id: int

    chunk_index: int

    content: str

    start_page: int

    end_page: int


@dataclass(frozen=True)
class RAGContext:
    """
    最终送给 LLM 的 Context。
    """

    text: str

    sources: list[
        RAGSource
    ]


def build_rag_context(
    candidates: list[
        RetrievalCandidate
    ],
    max_chars: int,
) -> RAGContext:
    """
    将 Retrieval Candidate
    转换成带 Source ID 的 Prompt Context。

    Example:

        [S1]
        Pages: 3-4
        ...

        [S2]
        Pages: 6
        ...
    """

    sources = []

    blocks = []

    used_chars = 0


    for candidate in candidates:

        source_id = (
            f"S{len(sources) + 1}"
        )


        if (
            candidate.start_page
            == candidate.end_page
        ):

            page_text = (
                str(
                    candidate.start_page
                )
            )


        else:

            page_text = (
                f"{candidate.start_page}"
                f"-"
                f"{candidate.end_page}"
            )


        block = (
            f"[{source_id}]\n"
            f"Pages: {page_text}\n"
            f"{candidate.content.strip()}"
        )


        projected_size = (
            used_chars
            + len(block)
            + 2
        )


        # 已有至少一条 Evidence 后，
        # 超出 Context Budget 就停止。
        if (
            sources
            and projected_size
            > max_chars
        ):
            break


        source = RAGSource(
            source_id=source_id,

            chunk_id=(
                candidate.chunk_id
            ),

            chunk_index=(
                candidate.chunk_index
            ),

            content=(
                candidate.content
            ),

            start_page=(
                candidate.start_page
            ),

            end_page=(
                candidate.end_page
            ),
        )


        sources.append(
            source
        )

        blocks.append(
            block
        )

        used_chars = (
            projected_size
        )


    return RAGContext(
        text="\n\n".join(
            blocks
        ),

        sources=sources,
    )