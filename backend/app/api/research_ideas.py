from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.dependencies import (
    get_current_user,
    get_db,
    get_embedding_provider,
    get_llm_provider,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.models.user import (
    User,
)
from backend.app.schemas.research_idea import (
    ResearchIdeaRequest,
    ResearchIdeaResponse,
)
from backend.app.services import (
    research_idea,
)


router = APIRouter(
    prefix="/projects",
    tags=[
        "Research Idea"
    ],
)


@router.post(
    "/{project_id}/research-ideas",
    response_model=(
        ResearchIdeaResponse
    ),
)
async def generate_research_ideas(
    project_id: int,
    request: ResearchIdeaRequest,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),

    embedding_provider: (
        EmbeddingProvider
    ) = Depends(
        get_embedding_provider
    ),

    llm_provider: (
        LLMProvider
    ) = Depends(
        get_llm_provider
    ),
) -> ResearchIdeaResponse:
    """
    基于：

        Paper Comparison
            ↓
        Verified Research Gap
            ↓
        Research Idea
            ↓
        Feasibility Review
            ↓
        Novelty Risk Review
            ↓
        Experiment Plan
    """

    return (
        await research_idea
        .generate_project_research_ideas(
            db=db,

            project_id=(
                project_id
            ),

            user_id=(
                current_user.id
            ),

            request=(
                request
            ),

            embedding_provider=(
                embedding_provider
            ),

            llm_provider=(
                llm_provider
            ),
        )
    )