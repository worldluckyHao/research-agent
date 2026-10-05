import pytest

# Import 会触发 Prompt Registration。
import backend.app.prompts.agent_evaluation
import backend.app.prompts.rag_evaluation

from backend.app.prompts.registry import (
    prompt_registry,
)


pytestmark = pytest.mark.unit


# ============================================================
# RAG Evaluation Prompt
# ============================================================

def test_rag_evaluation_prompt_renders():
    rendered = (
        prompt_registry.render(
            prompt_id=(
                "rag.evaluation.user"
            ),

            version=1,

            question=(
                "What is PWformer?"
            ),

            answer=(
                "PWformer is a model [S1]."
            ),

            evidence=(
                "[S1] PWformer is "
                "a Transformer model."
            ),
        )
    )


    assert (
        "What is PWformer?"
        in rendered
    )

    assert (
        "PWformer is a model [S1]."
        in rendered
    )

    assert (
        '"groundedness"'
        in rendered
    )


    # JSON 示例的大括号应该已经
    # 从 {{ }} 渲染为 { }。
    assert "{{" not in rendered

    assert "}}" not in rendered


# ============================================================
# Agent Evaluation Prompt
# ============================================================

def test_agent_evaluation_prompt_renders():
    rendered = (
        prompt_registry.render(
            prompt_id=(
                "agent.evaluation.user"
            ),

            version=1,

            task=(
                "Find the main method."
            ),

            tool_trace=(
                "Step 1: search"
            ),

            final_answer=(
                "The method is PWformer."
            ),

            reference_outcome=(
                "Identify PWformer."
            ),

            evidence=(
                "[S1] PWformer..."
            ),
        )
    )


    assert (
        "Find the main method."
        in rendered
    )

    assert (
        "Step 1: search"
        in rendered
    )

    assert (
        '"goal_completion"'
        in rendered
    )

    assert "{{" not in rendered

    assert "}}" not in rendered