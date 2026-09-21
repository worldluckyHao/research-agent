from typing import Optional

from pydantic import (
    BaseModel,
    Field,
)


# ============================================================
# Request
# ============================================================

class RAGQuestionRequest(
    BaseModel
):
    """
    Citation-Aware RAG 请求。
    """

    question: str = Field(
        min_length=2,
        max_length=1000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )

    use_reranker: bool = True


# ============================================================
# Citation
# ============================================================

class RAGCitationResponse(
    BaseModel
):
    """
    一个已经经过后端验证的引用。
    """

    source_id: str

    chunk_id: int

    chunk_index: int

    start_page: int

    end_page: int


# ============================================================
# Model Provenance
# ============================================================

class RAGModelInfoResponse(
    BaseModel
):
    """
    本次生成使用的 LLM 信息。
    """

    provider: str

    model_name: str


# ============================================================
# Prompt Provenance
# ============================================================

class RAGPromptInfoResponse(
    BaseModel
):
    """
    本次 RAG 使用的 Prompt Version 信息。

    System Prompt 与 User Prompt
    分别追踪。
    """

    system_prompt_id: str

    system_prompt_version: int

    user_prompt_id: str

    user_prompt_version: int


# ============================================================
# Response
# ============================================================

class RAGAnswerResponse(
    BaseModel
):
    """
    Citation-Aware RAG 最终响应。
    """

    document_id: int

    question: str

    answer: str

    # grounded=True 当前只代表：
    #
    # 1. 至少使用了合法 citation；
    # 2. 没有 invalid citation。
    #
    # 不代表答案一定事实正确。
    grounded: bool

    retrieval_count: int

    # 没有调用 LLM 时可能为 None。
    model: Optional[
        RAGModelInfoResponse
    ] = None

    # 没有真正 render / 调用 Prompt 时
    # 可以为 None。
    prompt: Optional[
        RAGPromptInfoResponse
    ] = None

    citations: list[
        RAGCitationResponse
    ]

    invalid_citations: list[str]