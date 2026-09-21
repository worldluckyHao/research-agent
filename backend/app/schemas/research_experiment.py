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
from backend.app.schemas.research_idea import (
    ResearchIdeaResponse,
    ResearchIdeaResult,
)
from backend.app.schemas.rag import (
    RAGModelInfoResponse,
    RAGPromptInfoResponse,
)


# ============================================================
# Request
# ============================================================

class ResearchExperimentRequest(
    BaseModel
):
    """
    Day41 Experiment Design Request（实验设计请求）。

    Pipeline：

        selected papers
            ↓
        research gap
            ↓
        research idea
            ↓
        selected idea
            ↓
        experiment protocol
    """

    # --------------------------------------------------------
    # Upstream paper sources
    # --------------------------------------------------------

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


    selected_gap_id: Optional[
        str
    ] = Field(
        default=None,
        max_length=20,
    )


    # --------------------------------------------------------
    # Idea Selection
    # --------------------------------------------------------

    # Example:
    # I1
    #
    # 如果不传：
    #
    # 1. 优先 recommended_for_experiment
    # 2. 再选择 needs_revision
    selected_idea_id: Optional[
        str
    ] = Field(
        default=None,
        max_length=20,
    )


    # --------------------------------------------------------
    # Research Constraints
    # --------------------------------------------------------

    constraints: Optional[
        str
    ] = Field(
        default=None,
        max_length=1000,
    )


    # 对实验设计的额外关注点。
    #
    # Example：
    #
    # "重点设计极端降水评估和统计显著性实验"
    experiment_focus: Optional[
        str
    ] = Field(
        default=None,
        max_length=1000,
    )


    response_language: Literal[
        "zh",
        "en",
    ] = "zh"


# ============================================================
# Research Question
# ============================================================

class ExperimentResearchQuestionResponse(
    BaseModel
):
    """
    一个可以通过实验回答的 Research Question。
    """

    question_id: str

    question: str

    hypothesis: str

    null_hypothesis: str

    # 用什么主要结果判断 Hypothesis。
    primary_outcome: str

    # Example:
    #
    # higher
    # lower
    # more robust
    expected_observation: str


# ============================================================
# Experimental Variables
# ============================================================

class ExperimentVariablesResponse(
    BaseModel
):
    """
    Experimental Variables（实验变量）。
    """

    independent_variables: list[
        str
    ] = Field(
        min_length=1
    )


    dependent_variables: list[
        str
    ] = Field(
        min_length=1
    )


    control_variables: list[
        str
    ] = Field(
        min_length=1
    )


    # 潜在 Confounder（混杂因素）。
    confounders: list[str]


# ============================================================
# Data Protocol
# ============================================================

class ExperimentDataProtocolResponse(
    BaseModel
):
    """
    数据与划分协议。
    """

    datasets: list[
        str
    ] = Field(
        min_length=1
    )


    sampling_unit: str


    # 使用字符串而不是强制百分比。
    #
    # 因为时间序列任务通常是：
    #
    # train = 2004-2020
    # validation = 2021
    # test = 2022-2024
    train_split: str

    validation_split: str

    test_split: str


    split_strategy: str


    preprocessing: list[str]


    # 防止 Train/Test 信息泄漏。
    leakage_controls: list[
        str
    ] = Field(
        min_length=1
    )


# ============================================================
# Baseline Protocol
# ============================================================

class ExperimentBaselineResponse(
    BaseModel
):
    """
    一项 Baseline 及公平比较协议。
    """

    name: str

    purpose: str

    fairness_controls: list[
        str
    ] = Field(
        min_length=1
    )


# ============================================================
# Ablation Protocol
# ============================================================

class ExperimentAblationResponse(
    BaseModel
):
    """
    一个 Ablation 对应一个明确 Claim。
    """

    name: str

    removed_or_changed_component: str

    tested_claim: str

    expected_observation: str


# ============================================================
# Hyperparameter Study
# ============================================================

class ExperimentHyperparameterResponse(
    BaseModel
):
    """
    Hyperparameter Study（超参数实验）。
    """

    parameter: str

    candidate_values: list[str]

    selection_rule: str


# ============================================================
# Statistical Analysis
# ============================================================

class ExperimentStatisticalPlanResponse(
    BaseModel
):
    """
    Statistical Analysis Plan（统计分析方案）。

    注意：

    repeated_runs：
        独立训练重复次数。

    analysis_unit：
        到底在哪个层级做统计分析。
    """

    repeated_runs: int = Field(
        ge=1,
        le=20,
    )


    seed_policy: str


    analysis_unit: str


    primary_test: str


    effect_size: str


    confidence_interval: str


    multiple_comparison_control: str


    alpha: float = Field(
        gt=0.0,
        le=0.10,
    )


# ============================================================
# Compute Plan
# ============================================================

class ExperimentComputePlanResponse(
    BaseModel
):
    """
    计算资源和运行计划。
    """

    hardware_assumption: str

    batch_strategy: str

    memory_risks: list[str]

    runtime_tracking: list[str]


# ============================================================
# Reproducibility
# ============================================================

class ExperimentReproducibilityResponse(
    BaseModel
):
    """
    Reproducibility Checklist（可复现性检查）。
    """

    random_seed_control: str

    environment_recording: list[str]

    data_versioning: list[str]

    model_checkpointing: list[str]

    logging_requirements: list[str]

    artifact_requirements: list[str]


# ============================================================
# Full Protocol
# ============================================================

class ResearchExperimentProtocolResponse(
    BaseModel
):
    """
    完整 Experiment Protocol（实验协议）。
    """

    objective: str


    research_questions: list[
        ExperimentResearchQuestionResponse
    ] = Field(
        min_length=1
    )


    variables: (
        ExperimentVariablesResponse
    )


    data_protocol: (
        ExperimentDataProtocolResponse
    )


    baselines: list[
        ExperimentBaselineResponse
    ] = Field(
        min_length=1
    )


    ablations: list[
        ExperimentAblationResponse
    ] = Field(
        min_length=1
    )


    hyperparameter_studies: list[
        ExperimentHyperparameterResponse
    ]


    primary_metrics: list[
        str
    ] = Field(
        min_length=1
    )


    secondary_metrics: list[str]


    statistical_plan: (
        ExperimentStatisticalPlanResponse
    )


    compute_plan: (
        ExperimentComputePlanResponse
    )


    reproducibility: (
        ExperimentReproducibilityResponse
    )


    execution_stages: list[
        str
    ] = Field(
        min_length=1
    )


# ============================================================
# Critic
# ============================================================

ExperimentDesignStatus = Literal[
    "ready",
    "needs_revision",
    "invalid",
]


class ExperimentDesignReviewResponse(
    BaseModel
):
    """
    Experiment Design Critic 输出。
    """

    status: ExperimentDesignStatus


    reason: str


    strengths: list[str]


    major_issues: list[str]


    minor_issues: list[str]


    # --------------------------------------------------------
    # Dedicated Checks
    # --------------------------------------------------------

    leakage_risks: list[str]

    baseline_fairness_risks: list[str]

    claim_test_mismatches: list[str]

    statistical_risks: list[str]

    reproducibility_risks: list[str]


    required_revisions: list[str]


# ============================================================
# Final Response
# ============================================================

class ResearchExperimentResponse(
    BaseModel
):
    """
    Day41 最终 Response。
    """

    project_id: int


    source_gap_id: str

    source_idea_id: str


    # 保留 Day40 全链路，
    # 前端可以继续查看 Idea 来源。
    research_idea: ResearchIdeaResponse


    selected_idea: ResearchIdeaResult


    experiment_protocol: (
        ResearchExperimentProtocolResponse
    )


    design_review: (
        ExperimentDesignReviewResponse
    )


    scope_note: str


    model: Optional[
        RAGModelInfoResponse
    ] = None


    prompt: Optional[
        RAGPromptInfoResponse
    ] = None