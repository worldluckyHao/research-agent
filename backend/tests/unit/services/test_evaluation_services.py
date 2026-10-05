import pytest

from backend.app.schemas.agent_evaluation import (
    AgentEvaluationEvidence,
    AgentEvaluationRequest,
    AgentToolCallRecord,
    ExpectedAgentToolCall,
)
from backend.app.schemas.rag_evaluation import (
    RAGEvaluationEvidence,
    RAGEvaluationRequest,
)
from backend.app.services.agent_evaluation import (
    evaluate_agent,
)
from backend.app.services.rag_evaluation import (
    evaluate_rag,
)


pytestmark = pytest.mark.unit


# ============================================================
# RAG Evaluation Service
# ============================================================

async def test_rag_evaluation_service_with_fake_llm(
    fake_llm_provider_factory,
):
    """
    不访问 Bailian。

    Fake LLM 返回固定 Judge JSON。
    """

    provider = (
        fake_llm_provider_factory(
            """
            {
              "groundedness": 0.95,
              "relevance": 0.90,
              "reason": "The answer is supported."
            }
            """
        )
    )


    request = (
        RAGEvaluationRequest(
            question=(
                "What method is proposed?"
            ),

            answer=(
                "The paper proposes "
                "PWformer [S1]."
            ),

            evidence=[
                RAGEvaluationEvidence(
                    source_id="S1",

                    content=(
                        "The paper proposes "
                        "PWformer."
                    ),
                ),
            ],

            gold_source_ids=[
                "S1"
            ],
        )
    )


    result = await evaluate_rag(
        request=request,

        llm_provider=provider,
    )


    assert (
        result.retrieval.available
        is True
    )

    assert (
        result.retrieval.recall_at_k
        ==
        1.0
    )

    assert (
        result.citation.citation_precision
        ==
        1.0
    )

    assert (
        result.llm_judge.status
        ==
        "completed"
    )

    assert (
        result.llm_judge.groundedness
        ==
        0.95
    )

    assert (
        result.llm_judge.relevance
        ==
        0.9
    )

    assert (
        result.quality_gate.passed
        is True
    )


# ============================================================
# Agent Evaluation Service
# ============================================================

async def test_agent_evaluation_service_with_fake_llm(
    fake_llm_provider_factory,
):
    provider = (
        fake_llm_provider_factory(
            """
            {
              "goal_completion": 0.95,
              "final_answer_quality": 0.90,
              "trajectory_coherence": 0.90,
              "evidence_groundedness": 0.95,
              "reason": "The agent completed the task."
            }
            """
        )
    )


    request = (
        AgentEvaluationRequest(
            task=(
                "Find the main method."
            ),

            final_answer=(
                "The paper proposes "
                "PWformer [S1]."
            ),

            tool_calls=[
                AgentToolCallRecord(
                    step=1,

                    tool_name=(
                        "local_document_search"
                    ),

                    arguments={
                        "query": "main method",
                    },

                    status="success",

                    output_summary=(
                        "Found PWformer."
                    ),
                ),
            ],

            expected_tool_calls=[
                ExpectedAgentToolCall(
                    tool_name=(
                        "local_document_search"
                    ),

                    arguments={
                        "query": "main method",
                    },
                ),
            ],

            reference_outcome=(
                "Identify PWformer."
            ),

            evidence=[
                AgentEvaluationEvidence(
                    source_id="S1",

                    content=(
                        "The paper proposes "
                        "PWformer."
                    ),
                ),
            ],
        )
    )


    result = await evaluate_agent(
        request=request,

        llm_provider=provider,
    )


    assert (
        result.tool_selection.f1
        ==
        1.0
    )

    assert (
        result.tool_execution.success_rate
        ==
        1.0
    )

    assert (
        result.llm_judge.status
        ==
        "completed"
    )

    assert (
        result.llm_judge.goal_completion
        ==
        0.95
    )

    assert (
        result.quality_gate.passed
        is True
    )


# ============================================================
# Judge Failure
# ============================================================

async def test_agent_evaluation_keeps_metrics_when_judge_fails(
    fake_llm_provider_factory,
):
    """
    Fake LLM 故意返回非法 JSON。

    验证 Fail-Soft：

        Deterministic Metrics
        仍然保留。

        Judge
        unavailable。

        Quality Gate
        fail。
    """

    provider = (
        fake_llm_provider_factory(
            "this is not valid json"
        )
    )


    request = (
        AgentEvaluationRequest(
            task=(
                "Find the main method."
            ),

            final_answer=(
                "PWformer."
            ),

            tool_calls=[
                AgentToolCallRecord(
                    step=1,

                    tool_name="search",

                    arguments={
                        "query": "PWformer"
                    },

                    status="success",

                    output_summary=(
                        "Found PWformer."
                    ),
                ),
            ],

            expected_tool_calls=[
                ExpectedAgentToolCall(
                    tool_name="search",

                    arguments={
                        "query": "PWformer"
                    },
                ),
            ],
        )
    )


    result = await evaluate_agent(
        request=request,

        llm_provider=provider,
    )


    # Deterministic Metrics
    # 不能因为 Judge 失败而丢失。
    assert (
        result.tool_selection.f1
        ==
        1.0
    )

    assert (
        result.tool_execution.success_rate
        ==
        1.0
    )


    # Semantic Judge 明确标记不可用。
    assert (
        result.llm_judge.status
        ==
        "unavailable"
    )


    # Judge 开启但不可用，
    # Quality Gate 必须失败。
    assert (
        result.quality_gate.passed
        is False
    )