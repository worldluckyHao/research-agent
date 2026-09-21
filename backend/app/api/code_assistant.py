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
from backend.app.schemas.code_assistant import (
    CodeAssistantRequest,
    CodeAssistantResponse,
)
from backend.app.services import (
    code_assistant,
)


router = APIRouter(
    prefix="/projects",
    tags=[
        "Code Assistant"
    ],
)


@router.post(
    "/{project_id}/code-proposals",
    response_model=(
        CodeAssistantResponse
    ),
)
async def generate_code_proposal(
    project_id: int,
    request: CodeAssistantRequest,

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
) -> CodeAssistantResponse:
    """
    Pipeline：

        Research Experiment
            ↓
        Code Plan
            ↓
        Patch Proposal
            ↓
        Safety Review
            ↓
        Validation Plan

    注意：

        这里只生成 Proposal，
        不直接修改仓库文件。
    """

    return (
        await code_assistant
        .generate_code_change_proposal(
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