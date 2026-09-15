from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalCandidate:
    """
    Retrieval Candidate（检索候选）。

    这是内部对象，
    不直接暴露给 API。
    """

    chunk_id: int

    chunk_index: int

    content: str

    start_page: int

    end_page: int

    token_count: int

    # Semantic Branch
    semantic_rank: int | None = None

    semantic_score: float | None = None

    # Lexical Branch
    lexical_rank: int | None = None

    lexical_score: float | None = None

    # Fusion
    rrf_score: float = 0.0

    # Reranking
    rerank_score: float | None = None