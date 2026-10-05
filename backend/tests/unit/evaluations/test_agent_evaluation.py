import pytest

from backend.app.evaluations.agent import (
    evaluate_tool_execution,
    evaluate_tool_selection,
    evaluate_trajectory,
)
from backend.app.schemas.agent_evaluation import (
    AgentToolCallRecord,
    ExpectedAgentToolCall,
)


pytestmark = pytest.mark.unit


# ============================================================
# Helpers
# ============================================================

def _actual_call(
    tool_name="local_document_search",
    query="main method",
    status="success",
):
    return (
        AgentToolCallRecord(
            step=1,

            tool_name=(
                tool_name
            ),

            arguments={
                "query": query,
            },

            status=status,

            output_summary=(
                "Test output"
            ),

            error=(
                None
                if status == "success"
                else "Test error"
            ),
        )
    )


def _expected_call(
    tool_name="local_document_search",
    query="main method",
):
    return (
        ExpectedAgentToolCall(
            tool_name=(
                tool_name
            ),

            arguments={
                "query": query,
            },
        )
    )


# ============================================================
# Tool Selection
# ============================================================

def test_tool_selection_exact_match():
    actual = [
        _actual_call()
    ]

    expected = [
        _expected_call()
    ]


    result = (
        evaluate_tool_selection(
            actual_calls=actual,
            expected_calls=expected,
        )
    )


    assert result.available is True

    assert result.matched_count == 1

    assert result.precision == 1.0

    assert result.recall == 1.0

    assert result.f1 == 1.0

    assert (
        result.exact_sequence_match
        is True
    )


def test_tool_selection_wrong_arguments_do_not_match():
    """
    Tool Name 相同，
    Arguments 不同，
    仍然应该判定不匹配。
    """

    actual = [
        _actual_call(
            query="weather forecast"
        )
    ]

    expected = [
        _expected_call(
            query="main method"
        )
    ]


    result = (
        evaluate_tool_selection(
            actual_calls=actual,
            expected_calls=expected,
        )
    )


    assert result.matched_count == 0

    assert result.precision == 0.0

    assert result.recall == 0.0

    assert result.f1 == 0.0

    assert (
        result.exact_sequence_match
        is False
    )


def test_tool_selection_without_reference_is_unavailable():
    actual = [
        _actual_call()
    ]


    result = (
        evaluate_tool_selection(
            actual_calls=actual,
            expected_calls=None,
        )
    )


    assert result.available is False

    assert result.actual_count == 1

    assert result.f1 is None


# ============================================================
# Tool Execution
# ============================================================

def test_tool_execution_success_rate():
    calls = [
        _actual_call(
            status="success"
        ),

        AgentToolCallRecord(
            step=2,

            tool_name=(
                "local_document_search"
            ),

            arguments={
                "query": "experiment",
            },

            status="error",

            output_summary=None,

            error="timeout",
        ),
    ]


    result = (
        evaluate_tool_execution(
            actual_calls=calls
        )
    )


    assert result.total_calls == 2

    assert result.successful_calls == 1

    assert result.failed_calls == 1

    assert result.success_rate == 0.5


# ============================================================
# Trajectory
# ============================================================

def test_trajectory_detects_repeated_exact_call():
    calls = [
        AgentToolCallRecord(
            step=1,

            tool_name="search",

            arguments={
                "query": "PWformer"
            },

            status="error",

            error="timeout",
        ),

        AgentToolCallRecord(
            step=2,

            tool_name="search",

            arguments={
                "query": "PWformer"
            },

            status="success",

            output_summary="Found result",
        ),
    ]


    result = evaluate_trajectory(
        actual_calls=calls
    )


    assert result.total_steps == 2

    assert (
        result.repeated_exact_calls
        ==
        1
    )

    assert result.has_tool_errors is True