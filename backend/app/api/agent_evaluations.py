from fastapi import (
    APIRouter,
    Depends,
)

from backend.app.dependencies import (
    get_llm_provider,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.schemas.agent_evaluation import (
    AgentEvaluationRequest,
    AgentEvaluationResponse,
)
from backend.app.services.agent_evaluation import (
    evaluate_agent,
)


router = APIRouter(
    prefix="/agent-evaluations",
    tags=[
        "agent-evaluations",
    ],
)


# ============================================================
# Evaluate Agent Run
# ============================================================

@router.post(
    "",
    response_model=(
        AgentEvaluationResponse
    ),
)
async def evaluate_agent_run(
    request: AgentEvaluationRequest,

    llm_provider: LLMProvider = Depends(
        get_llm_provider
    ),
) -> AgentEvaluationResponse:
    """
    Evaluate one observable Agent Run.

    Dimensions：

        Tool Selection
        Tool Execution
        Trajectory
        Goal Completion
        Final Answer Quality
        Evidence Groundedness
        Quality Gate
    """

    return (
        await evaluate_agent(
            request=request,

            llm_provider=(
                llm_provider
            ),
        )
    )