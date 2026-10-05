from typing import (
    List,
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)


# ============================================================
# Evidence
# ============================================================

class RAGEvaluationEvidence(
    BaseModel
):
    """
    单条 RAG Evidence。

    source_id：

        S1
        S2
        S3

    必须与最终答案中的：

        [S1]
        [S2]

    保持一致。
    """

    source_id: str = Field(
        min_length=1,
        max_length=50,
    )

    content: str = Field(
        min_length=1,
        max_length=20000,
    )


# ============================================================
# Request
# ============================================================

class RAGEvaluationRequest(
    BaseModel
):
    """
    单条 RAG Evaluation 请求。
    """

    question: str = Field(
        min_length=1,
        max_length=4000,
    )

    answer: str = Field(
        min_length=1,
        max_length=20000,
    )

    evidence: List[
        RAGEvaluationEvidence
    ] = Field(
        min_length=1,
        max_length=50,
    )


    # Gold Sources（人工标注相关来源）
    #
    # 例如：
    #
    # ["S1", "S3"]
    #
    # 如果没有 Gold Label，
    # Retrieval Metrics 会返回 unavailable。
    gold_source_ids: Optional[
        List[str]
    ] = None


# ============================================================
# Retrieval Metrics
# ============================================================

class RetrievalEvaluationMetrics(
    BaseModel
):
    """
    Retrieval 层评估结果。
    """

    available: bool

    precision_at_k: Optional[
        float
    ] = None

    recall_at_k: Optional[
        float
    ] = None

    hit_rate: Optional[
        float
    ] = None

    mrr: Optional[
        float
    ] = None


# ============================================================
# Citation Metrics
# ============================================================

class CitationEvaluationMetrics(
    BaseModel
):
    """
    Citation 层评估结果。
    """

    total_citations: int

    unique_citations: int

    valid_citations: int

    invalid_citations: int


    # 合法引用 / 总引用
    citation_precision: float


    # 答案引用到了多少 Retrieved Sources。
    source_citation_coverage: float


    invalid_source_ids: List[str]


# ============================================================
# LLM Judge
# ============================================================

class LLMJudgeEvaluation(
    BaseModel
):
    """
    LLM-as-a-Judge 结果。
    """

    status: Literal[
        "completed",
        "unavailable",
    ]


    # Answer 是否受到 Evidence 支撑。
    groundedness: Optional[
        float
    ] = None


    # Answer 是否真正回应 Question。
    relevance: Optional[
        float
    ] = None


    reason: Optional[
        str
    ] = None


# ============================================================
# Quality Gate
# ============================================================

class RAGQualityGate(
    BaseModel
):
    """
    自动质量门禁。

    passed=False：

    不代表系统崩溃，
    而代表该 Sample 没达到
    当前项目设置的质量要求。
    """

    passed: bool

    reasons: List[str]


# ============================================================
# Response
# ============================================================

class RAGEvaluationResponse(
    BaseModel
):
    """
    完整 RAG Evaluation Report。
    """

    question: str

    retrieval: RetrievalEvaluationMetrics

    citation: CitationEvaluationMetrics

    llm_judge: LLMJudgeEvaluation

    quality_gate: RAGQualityGate