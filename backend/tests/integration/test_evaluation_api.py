import pytest
from fastapi.testclient import (
    TestClient,
)

from backend.app.dependencies import (
    get_llm_provider,
)
from backend.app.main import (
    app,
)


pytestmark = pytest.mark.integration


# ============================================================
# RAG Evaluation API
# ============================================================

def test_rag_evaluation_api(
    fake_llm_provider_factory,
):
    """
    HTTP
      ↓
    FastAPI
      ↓
    Dependency Override
      ↓
    RAG Evaluation Service
      ↓
    Response
    """

    fake_provider = (
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


    # --------------------------------------------------------
    # Override Real Bailian
    # --------------------------------------------------------

    app.dependency_overrides[
        get_llm_provider
    ] = lambda: fake_provider


    client = TestClient(
        app
    )


    try:

        response = client.post(
            "/api/v1/rag-evaluations",

            json={
                "question": (
                    "What method is proposed?"
                ),

                "answer": (
                    "The paper proposes "
                    "PWformer [S1]."
                ),

                "evidence": [
                    {
                        "source_id": "S1",

                        "content": (
                            "The paper proposes "
                            "PWformer."
                        ),
                    }
                ],

                "gold_source_ids": [
                    "S1"
                ],
            },
        )


        assert (
            response.status_code
            ==
            200
        )


        data = response.json()


        assert (
            data["retrieval"][
                "recall_at_k"
            ]
            ==
            1.0
        )


        assert (
            data["citation"][
                "citation_precision"
            ]
            ==
            1.0
        )


        assert (
            data["llm_judge"][
                "status"
            ]
            ==
            "completed"
        )


        assert (
            data["llm_judge"][
                "groundedness"
            ]
            ==
            0.95
        )


        assert (
            data["quality_gate"][
                "passed"
            ]
            is True
        )


    finally:

        client.close()

        app.dependency_overrides.pop(
            get_llm_provider,
            None,
        )


# ============================================================
# Agent Evaluation API
# ============================================================

def test_agent_evaluation_api(
    fake_llm_provider_factory,
):
    fake_provider = (
        fake_llm_provider_factory(
            """
            {
              "goal_completion": 0.95,
              "final_answer_quality": 0.90,
              "trajectory_coherence": 0.90,
              "evidence_groundedness": 0.95,
              "reason": "The task was completed."
            }
            """
        )
    )


    app.dependency_overrides[
        get_llm_provider
    ] = lambda: fake_provider


    client = TestClient(
        app
    )


    try:

        response = client.post(
            "/api/v1/agent-evaluations",

            json={
                "task": (
                    "Find the main method."
                ),

                "final_answer": (
                    "The paper proposes "
                    "PWformer [S1]."
                ),

                "tool_calls": [
                    {
                        "step": 1,

                        "tool_name": (
                            "local_document_search"
                        ),

                        "arguments": {
                            "query": (
                                "main method"
                            )
                        },

                        "status": "success",

                        "output_summary": (
                            "Found PWformer."
                        ),

                        "error": None,
                    }
                ],

                "expected_tool_calls": [
                    {
                        "tool_name": (
                            "local_document_search"
                        ),

                        "arguments": {
                            "query": (
                                "main method"
                            )
                        },
                    }
                ],

                "reference_outcome": (
                    "Identify PWformer."
                ),

                "evidence": [
                    {
                        "source_id": "S1",

                        "content": (
                            "The paper proposes "
                            "PWformer."
                        ),
                    }
                ],
            },
        )


        assert (
            response.status_code
            ==
            200
        )


        data = response.json()


        assert (
            data["tool_selection"][
                "f1"
            ]
            ==
            1.0
        )


        assert (
            data["tool_execution"][
                "success_rate"
            ]
            ==
            1.0
        )


        assert (
            data["llm_judge"][
                "goal_completion"
            ]
            ==
            0.95
        )


        assert (
            data["quality_gate"][
                "passed"
            ]
            is True
        )


    finally:

        client.close()

        app.dependency_overrides.pop(
            get_llm_provider,
            None,
        )