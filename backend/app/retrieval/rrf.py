from dataclasses import replace

from backend.app.retrieval.base import (
    RetrievalCandidate,
)


def reciprocal_rank_fusion(
    semantic_candidates: list[
        RetrievalCandidate
    ],
    lexical_candidates: list[
        RetrievalCandidate
    ],
    rrf_k: int,
    limit: int,
) -> list[RetrievalCandidate]:
    """
    Reciprocal Rank Fusion
    （倒数排名融合）。

    Formula:

        score += 1 / (k + rank)

    不直接混合不同 Retriever
    的原始 Score。
    """

    if rrf_k <= 0:
        raise ValueError(
            "rrf_k must be positive"
        )


    merged: dict[
        int,
        RetrievalCandidate,
    ] = {}


    # ========================================================
    # Semantic Ranking
    # ========================================================

    for rank, candidate in enumerate(
        semantic_candidates,
        start=1,
    ):

        score = (
            1.0
            / (
                rrf_k
                + rank
            )
        )


        existing = merged.get(
            candidate.chunk_id
        )


        if existing is None:

            merged[
                candidate.chunk_id
            ] = replace(
                candidate,
                semantic_rank=rank,
                rrf_score=score,
            )


        else:

            merged[
                candidate.chunk_id
            ] = replace(
                existing,
                semantic_rank=rank,
                semantic_score=(
                    candidate
                    .semantic_score
                ),
                rrf_score=(
                    existing.rrf_score
                    + score
                ),
            )


    # ========================================================
    # Lexical Ranking
    # ========================================================

    for rank, candidate in enumerate(
        lexical_candidates,
        start=1,
    ):

        score = (
            1.0
            / (
                rrf_k
                + rank
            )
        )


        existing = merged.get(
            candidate.chunk_id
        )


        if existing is None:

            merged[
                candidate.chunk_id
            ] = replace(
                candidate,
                lexical_rank=rank,
                rrf_score=score,
            )


        else:

            merged[
                candidate.chunk_id
            ] = replace(
                existing,
                lexical_rank=rank,
                lexical_score=(
                    candidate
                    .lexical_score
                ),
                rrf_score=(
                    existing.rrf_score
                    + score
                ),
            )


    # ========================================================
    # Sort by Fusion Score
    # ========================================================

    fused = sorted(
        merged.values(),
        key=lambda item: (
            item.rrf_score
        ),
        reverse=True,
    )


    return fused[:limit]