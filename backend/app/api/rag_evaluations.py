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
from backend.app.schemas.rag_evaluation import (
    RAGEvaluationRequest,
    RAGEvaluationResponse,
)
from backend.app.services.rag_evaluation import (
    evaluate_rag,
)


router = APIRouter(
    prefix="/rag-evaluations",
    tags=[
        "rag-evaluations",
    ],
)


# ============================================================
# Evaluate One RAG Sample
# ============================================================

@router.post(
    "",
    response_model=(
        RAGEvaluationResponse
    ),
)
async def evaluate_rag_sample(
    request: RAGEvaluationRequest,

    llm_provider: LLMProvider = Depends(
        get_llm_provider
    ),
) -> RAGEvaluationResponse:
    """
    Evaluate one Citation-Aware
    RAG sample.

    Evaluation dimensions：

        Retrieval
        Citation
        Groundedness
        Relevance
        Quality Gate
    """

    return (
        await evaluate_rag(
            request=(
                request
            ),

            llm_provider=(
                llm_provider
            ),
        )
    )