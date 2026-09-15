from typing import Optional

from pydantic import (
    BaseModel,
    Field,
)


class HybridSearchRequest(
    BaseModel
):
    """
    Hybrid Retrieval Request。
    """

    query: str = Field(
        min_length=2,
        max_length=1000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    use_reranker: bool = True


class HybridSearchResultItem(
    BaseModel
):
    """
    Hybrid Retrieval 最终结果。
    """

    chunk_id: int

    chunk_index: int

    content: str

    start_page: int

    end_page: int

    token_count: int


    semantic_rank: Optional[int] = None

    semantic_score: Optional[
        float
    ] = None


    lexical_rank: Optional[int] = None

    lexical_score: Optional[
        float
    ] = None


    rrf_score: float

    rerank_score: Optional[
        float
    ] = None


class HybridSearchResponse(
    BaseModel
):
    """
    Hybrid Search Response。
    """

    document_id: int

    query: str

    top_k: int

    reranker_used: bool

    semantic_candidate_count: int

    lexical_candidate_count: int

    fused_candidate_count: int

    returned_count: int

    items: list[
        HybridSearchResultItem
    ]