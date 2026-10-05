import json
from collections import Counter
from typing import (
    List,
    Optional,
)

from backend.app.schemas.agent_evaluation import (
    AgentToolCallRecord,
    AgentTrajectoryMetrics,
    ExpectedAgentToolCall,
    ToolExecutionMetrics,
    ToolSelectionMetrics,
)


# ============================================================
# Canonical Tool Call
# ============================================================

def _canonical_tool_call(
    tool_name: str,
    arguments,
) -> str:
    """
    将 Tool Call 转成稳定字符串。

    例如：

        search
        {"query": "transformer"}

    即使 dict key 顺序不同，
    canonical result 仍保持一致。
    """

    arguments_json = json.dumps(
        arguments,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    )

    return (
        f"{tool_name.strip()}:"
        f"{arguments_json}"
    )


# ============================================================
# Unmatched Names
# ============================================================

def _collect_unmatched_names(
    calls,
    remaining: Counter,
) -> List[str]:
    """
    根据 Counter 恢复未匹配 Tool Name。
    """

    result = []

    working = remaining.copy()

    for call in calls:

        key = _canonical_tool_call(
            call.tool_name,
            call.arguments,
        )

        if working[key] > 0:

            result.append(
                call.tool_name
            )

            working[key] -= 1

    return result


# ============================================================
# Tool Selection
# ============================================================

def evaluate_tool_selection(
    actual_calls: List[
        AgentToolCallRecord
    ],

    expected_calls: Optional[
        List[
            ExpectedAgentToolCall
        ]
    ],
) -> ToolSelectionMetrics:
    """
    比较实际 Tool Calls 和 Gold Tool Calls。

    匹配条件：

        tool_name 相同
        +
        arguments 完全一致

    同时计算：

        Precision
        Recall
        F1
        Exact Sequence Match
    """

    actual_keys = [
        _canonical_tool_call(
            call.tool_name,
            call.arguments,
        )
        for call in actual_calls
    ]


    # --------------------------------------------------------
    # No Reference
    # --------------------------------------------------------

    if expected_calls is None:

        return (
            ToolSelectionMetrics(
                available=False,
                actual_count=(
                    len(actual_calls)
                ),
            )
        )


    expected_keys = [
        _canonical_tool_call(
            call.tool_name,
            call.arguments,
        )
        for call in expected_calls
    ]


    actual_counter = Counter(
        actual_keys
    )

    expected_counter = Counter(
        expected_keys
    )


    # Counter intersection：
    #
    # 既考虑 Tool Name，
    # 也考虑 Arguments，
    # 同时正确处理重复调用。
    matched_counter = (
        actual_counter
        &
        expected_counter
    )


    matched_count = sum(
        matched_counter.values()
    )


    actual_count = len(
        actual_calls
    )

    expected_count = len(
        expected_calls
    )


    # --------------------------------------------------------
    # Precision
    # --------------------------------------------------------

    if actual_count > 0:

        precision = (
            matched_count
            /
            actual_count
        )

    else:

        precision = (
            1.0
            if expected_count == 0
            else 0.0
        )


    # --------------------------------------------------------
    # Recall
    # --------------------------------------------------------

    if expected_count > 0:

        recall = (
            matched_count
            /
            expected_count
        )

    else:

        recall = 1.0


    # --------------------------------------------------------
    # F1
    # --------------------------------------------------------

    if (
        precision
        +
        recall
        >
        0.0
    ):

        f1 = (
            2.0
            *
            precision
            *
            recall
            /
            (
                precision
                +
                recall
            )
        )

    else:

        f1 = 0.0


    # --------------------------------------------------------
    # Missing / Unexpected
    # --------------------------------------------------------

    missing_counter = (
        expected_counter
        -
        actual_counter
    )

    unexpected_counter = (
        actual_counter
        -
        expected_counter
    )


    missing_tool_calls = (
        _collect_unmatched_names(
            expected_calls,
            missing_counter,
        )
    )


    unexpected_tool_calls = (
        _collect_unmatched_names(
            actual_calls,
            unexpected_counter,
        )
    )


    return (
        ToolSelectionMetrics(
            available=True,

            actual_count=(
                actual_count
            ),

            expected_count=(
                expected_count
            ),

            matched_count=(
                matched_count
            ),

            precision=round(
                precision,
                4,
            ),

            recall=round(
                recall,
                4,
            ),

            f1=round(
                f1,
                4,
            ),

            exact_sequence_match=(
                actual_keys
                ==
                expected_keys
            ),

            missing_tool_calls=(
                missing_tool_calls
            ),

            unexpected_tool_calls=(
                unexpected_tool_calls
            ),
        )
    )


# ============================================================
# Tool Execution
# ============================================================

def evaluate_tool_execution(
    actual_calls: List[
        AgentToolCallRecord
    ],
) -> ToolExecutionMetrics:
    """
    Tool Execution Success Rate。
    """

    total = len(
        actual_calls
    )


    successful = sum(
        1
        for call in actual_calls
        if call.status == "success"
    )


    failed = (
        total
        -
        successful
    )


    if total == 0:

        success_rate = 1.0

    else:

        success_rate = (
            successful
            /
            total
        )


    return (
        ToolExecutionMetrics(
            total_calls=total,

            successful_calls=(
                successful
            ),

            failed_calls=(
                failed
            ),

            success_rate=round(
                success_rate,
                4,
            ),
        )
    )


# ============================================================
# Trajectory
# ============================================================

def evaluate_trajectory(
    actual_calls: List[
        AgentToolCallRecord
    ],
) -> AgentTrajectoryMetrics:
    """
    只分析可观察的 Agent Trace。

    repeated_exact_calls 并不直接等于错误：

    Agent 可能因为第一次调用失败而重试。

    因此这里只记录，
    不直接判定为 Quality Gate Failure。
    """

    keys = [
        _canonical_tool_call(
            call.tool_name,
            call.arguments,
        )
        for call in actual_calls
    ]


    counts = Counter(
        keys
    )


    repeated_exact_calls = sum(
        max(
            count - 1,
            0,
        )
        for count in counts.values()
    )


    return (
        AgentTrajectoryMetrics(
            total_steps=(
                len(actual_calls)
            ),

            repeated_exact_calls=(
                repeated_exact_calls
            ),

            has_tool_errors=any(
                call.status == "error"
                for call in actual_calls
            ),
        )
    )