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
from backend.app.schemas.research_experiment import (
    ResearchExperimentRequest,
    ResearchExperimentResponse,
)
from backend.app.services import (
    research_experiment,
)


router = APIRouter(
    prefix="/projects",
    tags=[
        "Research Experiment"
    ],
)


@router.post(
    "/{project_id}/research-experiments",
    response_model=(
        ResearchExperimentResponse
    ),
)
async def design_research_experiment(
    project_id: int,
    request: ResearchExperimentRequest,

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
) -> ResearchExperimentResponse:
    """
    Pipeline：

        Paper Comparison
            ↓
        Research Gap
            ↓
        Research Idea
            ↓
        Experiment Design
            ↓
        Experiment Review
    """

    return (
        await research_experiment
        .design_project_research_experiment(
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