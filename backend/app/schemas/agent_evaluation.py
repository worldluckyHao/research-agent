from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)


# ============================================================
# Actual Tool Call
# ============================================================

class AgentToolCallRecord(BaseModel):
    """
    Agent 实际执行的一次 Tool Call。
    """

    step: int = Field(
        ge=1,
    )

    tool_name: str = Field(
        min_length=1,
        max_length=200,
    )

    arguments: Dict[
        str,
        Any,
    ] = Field(
        default_factory=dict,
    )

    status: Literal[
        "success",
        "error",
    ]

    output_summary: Optional[
        str
    ] = Field(
        default=None,
        max_length=4000,
    )

    error: Optional[
        str
    ] = Field(
        default=None,
        max_length=2000,
    )


# ============================================================
# Expected Tool Call
# ============================================================

class ExpectedAgentToolCall(BaseModel):
    """
    Gold / Reference Tool Call。

    用于比较：

        Agent 实际调用
        VS
        预期调用
    """

    tool_name: str = Field(
        min_length=1,
        max_length=200,
    )

    arguments: Dict[
        str,
        Any,
    ] = Field(
        default_factory=dict,
    )


# ============================================================
# Evidence
# ============================================================

class AgentEvaluationEvidence(BaseModel):
    """
    可选的 Agent 最终回答证据。
    """

    source_id: str = Field(
        min_length=1,
        max_length=100,
    )

    content: str = Field(
        min_length=1,
        max_length=20000,
    )


# ============================================================
# Request
# ============================================================

class AgentEvaluationRequest(BaseModel):
    """
    一次 Agent Run 的评估输入。
    """

    task: str = Field(
        min_length=1,
        max_length=4000,
    )

    final_answer: str = Field(
        min_length=1,
        max_length=20000,
    )

    tool_calls: List[
        AgentToolCallRecord
    ] = Field(
        default_factory=list,
        max_length=50,
    )


    # Gold Tool Calls。
    #
    # None：
    # 没有 Reference，
    # Tool Selection Metrics unavailable。
    expected_tool_calls: Optional[
        List[
            ExpectedAgentToolCall
        ]
    ] = None


    # 预期最终任务结果。
    #
    # 与 reference answer 不完全相同：
    # 它描述“任务应该完成到什么状态”。
    reference_outcome: Optional[
        str
    ] = Field(
        default=None,
        max_length=10000,
    )


    evidence: List[
        AgentEvaluationEvidence
    ] = Field(
        default_factory=list,
        max_length=50,
    )


# ============================================================
# Tool Selection Metrics
# ============================================================

class ToolSelectionMetrics(BaseModel):
    """
    Tool Selection Evaluation。
    """

    available: bool

    actual_count: int

    expected_count: Optional[
        int
    ] = None

    matched_count: Optional[
        int
    ] = None

    precision: Optional[
        float
    ] = None

    recall: Optional[
        float
    ] = None

    f1: Optional[
        float
    ] = None

    exact_sequence_match: Optional[
        bool
    ] = None

    missing_tool_calls: List[
        str
    ] = Field(
        default_factory=list,
    )

    unexpected_tool_calls: List[
        str
    ] = Field(
        default_factory=list,
    )


# ============================================================
# Tool Execution Metrics
# ============================================================

class ToolExecutionMetrics(BaseModel):
    """
    Tool 实际执行情况。
    """

    total_calls: int

    successful_calls: int

    failed_calls: int

    success_rate: float


# ============================================================
# Trajectory Metrics
# ============================================================

class AgentTrajectoryMetrics(BaseModel):
    """
    Agent 可观察执行轨迹统计。
    """

    total_steps: int

    repeated_exact_calls: int

    has_tool_errors: bool


# ============================================================
# LLM Judge
# ============================================================

class AgentJudgeEvaluation(BaseModel):
    """
    Agent LLM-as-a-Judge。
    """

    status: Literal[
        "completed",
        "unavailable",
    ]

    goal_completion: Optional[
        float
    ] = None

    final_answer_quality: Optional[
        float
    ] = None

    trajectory_coherence: Optional[
        float
    ] = None

    evidence_groundedness: Optional[
        float
    ] = None

    reason: Optional[
        str
    ] = None


# ============================================================
# Quality Gate
# ============================================================

class AgentQualityGate(BaseModel):
    """
    Agent Quality Gate。
    """

    passed: bool

    reasons: List[str] = Field(
        default_factory=list,
    )


# ============================================================
# Response
# ============================================================

class AgentEvaluationResponse(BaseModel):
    """
    完整 Agent Evaluation Report。
    """

    task: str

    tool_selection: ToolSelectionMetrics

    tool_execution: ToolExecutionMetrics

    trajectory: AgentTrajectoryMetrics

    llm_judge: AgentJudgeEvaluation

    quality_gate: AgentQualityGate