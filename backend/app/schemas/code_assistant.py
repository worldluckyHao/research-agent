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
from backend.app.schemas.research_experiment import (
    ResearchExperimentResponse,
)
from backend.app.schemas.rag import (
    RAGModelInfoResponse,
    RAGPromptInfoResponse,
)


# ============================================================
# Request
# ============================================================

class CodeAssistantRequest(
    BaseModel
):
    """
    Day42 Code Assistant Request。

    Pipeline:

        selected papers
            ↓
        research gap
            ↓
        research idea
            ↓
        experiment design
            ↓
        code planning
    """

    # --------------------------------------------------------
    # Upstream Context
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


    selected_idea_id: Optional[
        str
    ] = Field(
        default=None,
        max_length=20,
    )


    constraints: Optional[
        str
    ] = Field(
        default=None,
        max_length=1000,
    )


    experiment_focus: Optional[
        str
    ] = Field(
        default=None,
        max_length=1000,
    )


    # --------------------------------------------------------
    # Code Scope
    # --------------------------------------------------------

    # 代码目标根目录。
    #
    # 注意：
    # Day42 只是逻辑 Scope，
    # 不会真的访问或写入文件系统。
    target_root: str = Field(
        default="research/",
        min_length=1,
        max_length=300,
    )


    # 用户允许 Code Assistant
    # 修改的相对目录。
    #
    # Example:
    #
    # [
    #   "research/models/",
    #   "research/configs/",
    #   "research/tests/"
    # ]
    allowed_paths: list[
        str
    ] = Field(
        default_factory=lambda: [
            "research/models/",
            "research/configs/",
            "research/tests/",
        ],
        min_length=1,
        max_length=20,
    )


    # --------------------------------------------------------
    # Generation Preferences
    # --------------------------------------------------------

    include_code_skeletons: bool = True


    include_tests: bool = True


    max_file_changes: int = Field(
        default=8,
        ge=1,
        le=20,
    )


    response_language: Literal[
        "zh",
        "en",
    ] = "zh"


# ============================================================
# File Operation
# ============================================================

CodeFileOperation = Literal[
    "create",
    "modify",
    "no_change",
]


CodePatchRisk = Literal[
    "low",
    "medium",
    "high",
]


# ============================================================
# File Plan
# ============================================================

class CodeFilePlanResponse(
    BaseModel
):
    """
    Code Planner 输出的一项 File Plan。
    """

    file_path: str


    operation: CodeFileOperation


    purpose: str


    dependencies: list[str]


    affected_components: list[str]


# ============================================================
# Patch Proposal
# ============================================================

class CodePatchProposalResponse(
    BaseModel
):
    """
    Patch Proposal（代码补丁提案）。

    Day42 不真正写文件，
    只输出这一结构。
    """

    file_path: str


    operation: CodeFileOperation


    purpose: str


    # create:
    #     完整文件骨架
    #
    # modify:
    #     说明建议修改块
    code: Optional[str] = None


    insertion_or_replacement_hint: str


    imports_required: list[str]


    risks: list[str]


# ============================================================
# Validation Step
# ============================================================

class CodeValidationStepResponse(
    BaseModel
):
    """
    一个验证步骤。
    """

    stage: Literal[
        "import",
        "unit_test",
        "integration_test",
        "api_test",
        "training_smoke_test",
        "static_check",
        "manual_review",
    ]


    command_or_action: str


    expected_result: str


    purpose: str


# ============================================================
# Safety Review
# ============================================================

CodeSafetyStatus = Literal[
    "safe_to_review",
    "needs_manual_review",
    "rejected",
]


class CodeSafetyReviewResponse(
    BaseModel
):
    """
    Code Safety Reviewer 输出。
    """

    status: CodeSafetyStatus


    reason: str


    path_violations: list[str]


    destructive_change_risks: list[str]


    architecture_risks: list[str]


    dependency_risks: list[str]


    test_gaps: list[str]


    required_revisions: list[str]


# ============================================================
# Final Response
# ============================================================

class CodeAssistantResponse(
    BaseModel
):
    """
    Day42 最终 Response。
    """

    project_id: int


    source_gap_id: str


    source_idea_id: str


    experiment: (
        ResearchExperimentResponse
    )


    # --------------------------------------------------------
    # Planning
    # --------------------------------------------------------

    file_plan: list[
        CodeFilePlanResponse
    ]


    # --------------------------------------------------------
    # Proposed Changes
    # --------------------------------------------------------

    patches: list[
        CodePatchProposalResponse
    ]


    # --------------------------------------------------------
    # Safety
    # --------------------------------------------------------

    safety_review: (
        CodeSafetyReviewResponse
    )


    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    validation_plan: list[
        CodeValidationStepResponse
    ]


    # --------------------------------------------------------
    # Important Boundary
    # --------------------------------------------------------

    execution_note: str


    model: Optional[
        RAGModelInfoResponse
    ] = None


    prompt: Optional[
        RAGPromptInfoResponse
    ] = None