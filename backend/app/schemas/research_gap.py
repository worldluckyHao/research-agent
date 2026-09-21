from typing import (
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from backend.app.schemas.paper_comparison import (
    PaperComparisonCitationResponse,
    PaperComparisonItemRequest,
    PaperComparisonResponse,
)
from backend.app.schemas.rag import (
    RAGModelInfoResponse,
    RAGPromptInfoResponse,
)


# ============================================================
# Request
# ============================================================

class ResearchGapRequest(
    BaseModel
):
    """
    Day39 Research Gap 请求。

    items:
        要分析的论文与文档。

    comparison_focus:
        Day38 Paper Comparison 的关注维度。

    gap_focus:
        Day39 Research Gap 关注领域。

    max_candidates:
        最多生成多少个 Gap Candidate。

    response_language:
        返回中文 / 英文。
    """

    items: list[
        PaperComparisonItemRequest
    ] = Field(
        min_length=2,
        max_length=10,
    )


    comparison_focus: Optional[
        str
    ] = Field(
        default=None,
        max_length=500,
    )


    gap_focus: Optional[
        str
    ] = Field(
        default=None,
        max_length=500,
    )


    max_candidates: int = Field(
        default=5,
        ge=1,
        le=10,
    )


    response_language: Literal[
        "zh",
        "en",
    ] = "zh"


    @model_validator(
        mode="after"
    )
    def validate_unique_sources(
        self,
    ):
        """
        同一个 Research Gap Analysis 中：

        Paper 不能重复。
        Document 不能重复。
        """

        paper_ids = [
            item.paper_id
            for item in self.items
        ]


        document_ids = [
            item.document_id
            for item in self.items
        ]


        if (
            len(paper_ids)
            != len(set(paper_ids))
        ):

            raise ValueError(
                (
                    "Each paper can only appear "
                    "once in research gap analysis"
                )
            )


        if (
            len(document_ids)
            != len(set(document_ids))
        ):

            raise ValueError(
                (
                    "Each document can only appear "
                    "once in research gap analysis"
                )
            )


        return self


# ============================================================
# Gap Candidate
# ============================================================

ResearchGapType = Literal[
    "method_gap",
    "data_gap",
    "modality_gap",
    "evaluation_gap",
    "robustness_gap",
    "generalization_gap",
    "interpretability_gap",
    "efficiency_gap",
    "reproducibility_gap",
    "scope_gap",
    "other",
]


ResearchGapVerificationStatus = Literal[
    "supported",
    "partially_supported",
    "rejected",
]


ResearchGapEvidenceStrength = Literal[
    "weak",
    "moderate",
    "strong",
]


# ============================================================
# Evidence Reference
# ============================================================

class ResearchGapEvidenceResponse(
    BaseModel
):
    """
    Research Gap 使用的一条 Evidence。

    直接复用 Day38 Citation Namespace：

        P1-S1
        P2-S3
    """

    citation_id: str

    paper_id: int

    document_id: int

    chunk_id: int

    chunk_index: int

    start_page: int

    end_page: int


# ============================================================
# Gap Result
# ============================================================

class ResearchGapCandidateResponse(
    BaseModel
):
    """
    一个经过 Verification 的 Gap Candidate。
    """

    # G1 / G2 / G3 ...
    gap_id: str


    title: str


    gap_type: ResearchGapType


    # --------------------------------------------------------
    # Gap Statement
    # --------------------------------------------------------

    gap_statement: str


    # 为什么这些 Evidence
    # 可以支持这一 Gap。
    evidence_basis: str


    # --------------------------------------------------------
    # Verification
    # --------------------------------------------------------

    verification_status: (
        ResearchGapVerificationStatus
    )


    verification_reason: str


    # --------------------------------------------------------
    # Evidence Strength
    # --------------------------------------------------------

    # 注意：
    #
    # 这不是统计概率。
    #
    # 只是当前 Selected Corpus 中的
    # Evidence Coverage 描述。
    evidence_strength: (
        ResearchGapEvidenceStrength
    )


    distinct_supporting_papers: int


    # --------------------------------------------------------
    # Evidence
    # --------------------------------------------------------

    supporting_evidence: list[
        ResearchGapEvidenceResponse
    ]


    counter_evidence: list[
        ResearchGapEvidenceResponse
    ]


    # --------------------------------------------------------
    # Scope
    # --------------------------------------------------------

    # 明确 Gap 成立范围。
    scope_limitations: str


# ============================================================
# Rejected Candidate
# ============================================================

class RejectedResearchGapResponse(
    BaseModel
):
    """
    被 Verifier 拒绝的 Research Gap。

    为什么仍返回？

    因为这有助于：
        Debug
        Evaluation
        可解释性
    """

    gap_id: str

    title: str

    gap_statement: str

    reason: str


# ============================================================
# Final Response
# ============================================================

class ResearchGapResponse(
    BaseModel
):
    """
    Day39 最终 Response。
    """

    project_id: int


    paper_count: int


    # --------------------------------------------------------
    # Upstream Comparison
    # --------------------------------------------------------

    # 保留 Day38 的完整 Comparison，
    # 这样前端可以继续查看：
    #
    # Paper Summary
    # Matrix
    # Key Differences
    comparison: PaperComparisonResponse


    # --------------------------------------------------------
    # Gap Results
    # --------------------------------------------------------

    gaps: list[
        ResearchGapCandidateResponse
    ]


    rejected_candidates: list[
        RejectedResearchGapResponse
    ]


    # --------------------------------------------------------
    # Scope Note
    # --------------------------------------------------------

    # 非常重要：
    #
    # 当前 Gap 仅代表 Selected Corpus。
    scope_note: str


    # --------------------------------------------------------
    # Provenance
    # --------------------------------------------------------

    model: Optional[
        RAGModelInfoResponse
    ] = None


    prompt: Optional[
        RAGPromptInfoResponse
    ] = None