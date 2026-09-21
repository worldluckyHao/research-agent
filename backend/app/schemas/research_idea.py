from typing import (
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)

from backend.app.schemas.paper_comparison import (
    PaperComparisonItemRequest,
)
from backend.app.schemas.research_gap import (
    ResearchGapResponse,
)
from backend.app.schemas.rag import (
    RAGModelInfoResponse,
    RAGPromptInfoResponse,
)


# ============================================================
# Request
# ============================================================

class ResearchIdeaRequest(
    BaseModel
):
    """
    Day40 Research Idea 请求。

    Flow:

        selected papers
            ↓
        Day39 research gap
            ↓
        selected gap
            ↓
        research idea generation
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


    # 用户可以指定想基于哪个 Gap。
    #
    # Example:
    # G1
    #
    # 如果为空：
    # Service 默认选择第一个
    # supported / partially_supported Gap。
    selected_gap_id: Optional[
        str
    ] = Field(
        default=None,
        max_length=20,
    )


    # 用户额外的研究约束。
    #
    # Example:
    #
    # "必须使用公开数据集"
    # "单卡 RTX 4090 可训练"
    # "希望适用于 6-48h 降水预测"
    constraints: Optional[
        str
    ] = Field(
        default=None,
        max_length=1000,
    )


    max_ideas: int = Field(
        default=3,
        ge=1,
        le=5,
    )


    response_language: Literal[
        "zh",
        "en",
    ] = "zh"


# ============================================================
# Idea Status / Risk
# ============================================================

ResearchIdeaFeasibility = Literal[
    "high",
    "medium",
    "low",
]


ResearchIdeaNoveltyRisk = Literal[
    "low",
    "medium",
    "high",
]


ResearchIdeaDecision = Literal[
    "recommended_for_experiment",
    "needs_revision",
    "rejected",
]


# ============================================================
# Candidate
# ============================================================

class ResearchIdeaCandidateResponse(
    BaseModel
):
    """
    Generator 产生的 Candidate Idea。
    """

    idea_id: str

    title: str

    problem_statement: str

    core_hypothesis: str

    proposed_method: str

    expected_contribution: str


# ============================================================
# Critic Results
# ============================================================

class FeasibilityReviewResponse(
    BaseModel
):
    """
    可行性审查。
    """

    feasibility: ResearchIdeaFeasibility

    reason: str

    data_risks: list[str]

    compute_risks: list[str]

    implementation_risks: list[str]

    suggested_revisions: list[str]


class NoveltyRiskReviewResponse(
    BaseModel
):
    """
    创新风险审查。

    注意：
    novelty_risk != novelty score
    """

    novelty_risk: ResearchIdeaNoveltyRisk

    reason: str

    overlap_risks: list[str]

    incremental_risks: list[str]

    claims_to_avoid: list[str]

    verification_needed: list[str]


# ============================================================
# Implementation Plan
# ============================================================

class ResearchIdeaExperimentPlan(
    BaseModel
):
    """
    可直接用于实验设计的计划。
    """

    datasets: list[str]

    inputs: list[str]

    prediction_target: str

    architecture: list[str]

    training_strategy: list[str]

    losses: list[str]

    baselines: list[str]

    ablations: list[str]

    metrics: list[str]

    experiments: list[str]

    implementation_steps: list[str]


# ============================================================
# Final Idea
# ============================================================

class ResearchIdeaResult(
    BaseModel
):
    """
    经过两个 Critic + Planner 后
    的最终 Idea。
    """

    idea_id: str

    title: str

    source_gap_id: str

    source_gap_statement: str

    problem_statement: str

    core_hypothesis: str

    proposed_method: str

    expected_contribution: str


    # --------------------------------------------------------
    # Reviews
    # --------------------------------------------------------

    feasibility_review: (
        FeasibilityReviewResponse
    )

    novelty_review: (
        NoveltyRiskReviewResponse
    )


    # --------------------------------------------------------
    # Decision
    # --------------------------------------------------------

    decision: ResearchIdeaDecision

    decision_reason: str


    # --------------------------------------------------------
    # Implementation
    # --------------------------------------------------------

    experiment_plan: Optional[
        ResearchIdeaExperimentPlan
    ] = None


    # --------------------------------------------------------
    # Important Scientific Scope
    # --------------------------------------------------------

    novelty_scope_note: str


# ============================================================
# Rejected Idea
# ============================================================

class RejectedResearchIdeaResponse(
    BaseModel
):
    idea_id: str

    title: str

    reason: str


# ============================================================
# Final Response
# ============================================================

class ResearchIdeaResponse(
    BaseModel
):
    """
    Day40 API Response。
    """

    project_id: int

    source_gap_id: str

    research_gap: ResearchGapResponse

    ideas: list[
        ResearchIdeaResult
    ]

    rejected_ideas: list[
        RejectedResearchIdeaResponse
    ]

    scope_note: str

    model: Optional[
        RAGModelInfoResponse
    ] = None

    prompt: Optional[
        RAGPromptInfoResponse
    ] = None