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
from backend.app.schemas.research_gap import (
    ResearchGapRequest,
    ResearchGapResponse,
)
from backend.app.services import (
    research_gap,
)


router = APIRouter(
    prefix="/projects",
    tags=[
        "Research Gap"
    ],
)


@router.post(
    "/{project_id}/research-gaps",
    response_model=(
        ResearchGapResponse
    ),
)
async def discover_research_gaps(
    project_id: int,
    request: ResearchGapRequest,

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
) -> ResearchGapResponse:
    """
    对 Research Project 中
    选择的多篇论文执行：

        Paper Comparison
            ↓
        Research Gap Discovery
            ↓
        Gap Verification
    """

    return (
        await research_gap
        .discover_project_research_gaps(
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