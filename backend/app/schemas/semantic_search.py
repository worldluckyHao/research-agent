from pydantic import (
    BaseModel,
    Field,
)


class SemanticSearchRequest(BaseModel):
    """
    Semantic Search Request
    （语义检索请求）。
    """

    query: str = Field(
        min_length=2,
        max_length=1000,
        description=(
            "Natural language question "
            "or search query"
        ),
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description=(
            "Maximum number of relevant "
            "chunks to return"
        ),
    )

    min_score: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description=(
            "Minimum cosine similarity "
            "score"
        ),
    )


class SemanticSearchResultItem(
    BaseModel
):
    """
    一个 Semantic Retrieval Result。
    """

    chunk_id: int

    chunk_index: int

    content: str

    start_page: int

    end_page: int

    token_count: int

    similarity_score: float

    cosine_distance: float


class SemanticSearchModelInfo(
    BaseModel
):
    """
    当前 Retrieval 使用的
    Embedding Model 信息。
    """

    provider: str

    model_name: str

    dimension: int


class SemanticSearchResponse(
    BaseModel
):
    """
    Semantic Search Response。
    """

    document_id: int

    query: str

    top_k: int

    min_score: float

    returned_count: int

    model: SemanticSearchModelInfo

    items: list[
        SemanticSearchResultItem
    ]