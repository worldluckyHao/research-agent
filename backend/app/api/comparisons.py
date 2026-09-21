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
from backend.app.schemas.paper_comparison import (
    PaperComparisonRequest,
    PaperComparisonResponse,
)
from backend.app.services import (
    paper_comparison,
)


router = APIRouter(
    prefix="/projects",
    tags=[
        "Paper Comparison"
    ],
)


@router.post(
    "/{project_id}/compare",
    response_model=(
        PaperComparisonResponse
    ),
)
async def compare_project_papers(
    project_id: int,
    request: PaperComparisonRequest,

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
) -> PaperComparisonResponse:
    """
    比较 Research Project 中
    指定的多篇论文。

    最少：
        2 篇

    默认最大：
        5 篇
    """

    return (
        await paper_comparison
        .compare_project_papers(
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