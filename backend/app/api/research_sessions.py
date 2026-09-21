from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
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
from backend.app.schemas.research_session import (
    ConversationAskRequest,
    ConversationTurnResponse,
    ResearchConversationCreate,
    ResearchConversationListResponse,
    ResearchConversationResponse,
    ResearchMessageListResponse,
    ResearchSessionCreate,
    ResearchSessionListResponse,
    ResearchSessionResponse,
)
from backend.app.services import (
    research_session,
)


router = APIRouter(
    prefix="/research-sessions",
    tags=["research-sessions"],
)


# ============================================================
# Session
# ============================================================

@router.post(
    "",
    response_model=(
        ResearchSessionResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
)
async def create_research_session(
    payload: ResearchSessionCreate,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    创建新的 Research Session。
    """

    return (
        await research_session
        .create_session(
            db=db,
            user_id=current_user.id,
            title=payload.title,
        )
    )


@router.get(
    "",
    response_model=(
        ResearchSessionListResponse
    ),
)
async def list_research_sessions(
    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    查看当前用户的 Research Sessions。
    """

    items, total = (
        await research_session
        .list_sessions(
            db=db,
            user_id=current_user.id,
            page=page,
            page_size=page_size,
        )
    )


    return (
        ResearchSessionListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get(
    "/{session_id}",
    response_model=(
        ResearchSessionResponse
    ),
)
async def get_research_session(
    session_id: int,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):
    return (
        await research_session
        .get_owned_session(
            db=db,
            session_id=session_id,
            user_id=current_user.id,
        )
    )


# ============================================================
# Conversation
# ============================================================

@router.post(
    "/{session_id}/conversations",
    response_model=(
        ResearchConversationResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
)
async def create_research_conversation(
    session_id: int,

    payload: ResearchConversationCreate,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    在 Research Session 下创建 Conversation。
    """

    return (
        await research_session
        .create_conversation(
            db=db,

            session_id=session_id,

            user_id=(
                current_user.id
            ),

            title=(
                payload.title
            ),

            paper_id=(
                payload.paper_id
            ),

            document_id=(
                payload.document_id
            ),
        )
    )


@router.get(
    "/{session_id}/conversations",
    response_model=(
        ResearchConversationListResponse
    ),
)
async def list_research_conversations(
    session_id: int,

    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):
    items, total = (
        await research_session
        .list_conversations(
            db=db,

            session_id=session_id,

            user_id=(
                current_user.id
            ),

            page=page,

            page_size=page_size,
        )
    )


    return (
        ResearchConversationListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    )


# ============================================================
# Messages
# ============================================================

@router.get(
    (
        "/{session_id}/conversations/"
        "{conversation_id}/messages"
    ),
    response_model=(
        ResearchMessageListResponse
    ),
)
async def list_conversation_messages(
    session_id: int,
    conversation_id: int,

    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=50,
        ge=1,
        le=100,
    ),

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),
):
    """
    查看 Conversation 历史消息。
    """

    items, total = (
        await research_session
        .list_messages(
            db=db,

            session_id=session_id,

            conversation_id=(
                conversation_id
            ),

            user_id=(
                current_user.id
            ),

            page=page,

            page_size=page_size,
        )
    )


    return (
        ResearchMessageListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post(
    (
        "/{session_id}/conversations/"
        "{conversation_id}/messages"
    ),
    response_model=(
        ConversationTurnResponse
    ),
)
async def ask_conversation(
    session_id: int,
    conversation_id: int,

    payload: ConversationAskRequest,

    db: AsyncSession = Depends(
        get_db
    ),

    current_user: User = Depends(
        get_current_user
    ),

    embedding_provider: EmbeddingProvider = Depends(
        get_embedding_provider
    ),

    llm_provider: LLMProvider = Depends(
        get_llm_provider
    ),
):
    """
    Persistent Conversational RAG。

    保存：
        User Message
        Assistant Message
        Citation Metadata
        Model Metadata
    """

    return (
        await research_session
        .ask_conversation_question(
            db=db,

            session_id=session_id,

            conversation_id=(
                conversation_id
            ),

            user_id=(
                current_user.id
            ),

            question=(
                payload.question
            ),

            top_k=(
                payload.top_k
            ),

            use_reranker=(
                payload.use_reranker
            ),

            embedding_provider=(
                embedding_provider
            ),

            llm_provider=(
                llm_provider
            ),
        )
    )