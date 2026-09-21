from datetime import (
    datetime,
    timezone,
)
from typing import Optional

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)
from sqlalchemy.orm import (
    selectinload,
)

from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    ConversationDocumentRequiredException,
    ResearchConversationNotFoundException,
    ResearchSessionNotFoundException,
)
from backend.app.embeddings.base import (
    EmbeddingProvider,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.models.research_conversation import (
    ResearchConversation,
)
from backend.app.models.research_message import (
    ResearchMessage,
)
from backend.app.models.research_session import (
    ResearchSession,
)
from backend.app.schemas.research_session import (
    ConversationTurnResponse,
)
from backend.app.services import (
    paper_document,
    rag_service,
)


# ============================================================
# Research Session
# ============================================================

async def create_session(
    db: AsyncSession,
    user_id: int,
    title: str,
) -> ResearchSession:
    """
    创建 Research Session。
    """

    session = ResearchSession(
        owner_id=user_id,
        title=title.strip(),
    )


    db.add(
        session
    )


    await db.commit()

    await db.refresh(
        session
    )


    return session


async def get_owned_session(
    db: AsyncSession,
    session_id: int,
    user_id: int,
) -> ResearchSession:
    """
    获取当前 User 拥有的 Session。

    不区分：
        Session 不存在
        Session 属于别人

    统一 404，
    防止 Resource Enumeration。
    """

    result = await db.execute(
        select(
            ResearchSession
        ).where(
            ResearchSession.id
            == session_id,

            ResearchSession.owner_id
            == user_id,
        )
    )


    session = (
        result.scalar_one_or_none()
    )


    if session is None:

        raise (
            ResearchSessionNotFoundException()
        )


    return session


async def list_sessions(
    db: AsyncSession,
    user_id: int,
    page: int,
    page_size: int,
) -> tuple[
    list[ResearchSession],
    int,
]:
    """
    分页获取当前用户的 Research Sessions。
    """

    offset = (
        page - 1
    ) * page_size


    count_result = await db.execute(
        select(
            func.count(
                ResearchSession.id
            )
        ).where(
            ResearchSession.owner_id
            == user_id
        )
    )


    total = (
        count_result.scalar_one()
    )


    result = await db.execute(
        select(
            ResearchSession
        )
        .where(
            ResearchSession.owner_id
            == user_id
        )
        .order_by(
            ResearchSession
            .updated_at
            .desc()
        )
        .offset(
            offset
        )
        .limit(
            page_size
        )
    )


    return (
        list(
            result.scalars().all()
        ),
        total,
    )


# ============================================================
# Research Conversation
# ============================================================

async def create_conversation(
    db: AsyncSession,
    session_id: int,
    user_id: int,
    title: str,
    paper_id: Optional[int],
    document_id: Optional[int],
) -> ResearchConversation:
    """
    在 Session 下创建 Conversation。

    如果绑定 PaperDocument，
    必须先执行 Document 权限检查。
    """

    await get_owned_session(
        db=db,
        session_id=session_id,
        user_id=user_id,
    )


    resolved_document_id = None


    if (
        paper_id is not None
        and document_id is not None
    ):

        document = (
            await paper_document
            .get_document(
                db=db,
                paper_id=paper_id,
                document_id=document_id,
                user_id=user_id,
            )
        )


        resolved_document_id = (
            document.id
        )


    conversation = (
        ResearchConversation(
            session_id=(
                session_id
            ),

            document_id=(
                resolved_document_id
            ),

            title=(
                title.strip()
            ),
        )
    )


    db.add(
        conversation
    )


    await db.commit()

    await db.refresh(
        conversation
    )


    return conversation


async def get_owned_conversation(
    db: AsyncSession,
    session_id: int,
    conversation_id: int,
    user_id: int,
) -> ResearchConversation:
    """
    获取当前用户拥有的 Conversation。
    """

    result = await db.execute(
        select(
            ResearchConversation
        )
        .join(
            ResearchSession,

            ResearchSession.id
            == ResearchConversation.session_id,
        )
        .options(
            selectinload(
                ResearchConversation.document
            )
        )
        .where(
            ResearchConversation.id
            == conversation_id,

            ResearchConversation.session_id
            == session_id,

            ResearchSession.owner_id
            == user_id,
        )
    )


    conversation = (
        result.scalar_one_or_none()
    )


    if conversation is None:

        raise (
            ResearchConversationNotFoundException()
        )


    return conversation


async def list_conversations(
    db: AsyncSession,
    session_id: int,
    user_id: int,
    page: int,
    page_size: int,
) -> tuple[
    list[ResearchConversation],
    int,
]:
    """
    分页获取 Session 下的 Conversations。
    """

    await get_owned_session(
        db=db,
        session_id=session_id,
        user_id=user_id,
    )


    offset = (
        page - 1
    ) * page_size


    count_result = await db.execute(
        select(
            func.count(
                ResearchConversation.id
            )
        ).where(
            ResearchConversation.session_id
            == session_id
        )
    )


    total = (
        count_result.scalar_one()
    )


    result = await db.execute(
        select(
            ResearchConversation
        )
        .where(
            ResearchConversation.session_id
            == session_id
        )
        .order_by(
            ResearchConversation
            .updated_at
            .desc()
        )
        .offset(
            offset
        )
        .limit(
            page_size
        )
    )


    return (
        list(
            result.scalars().all()
        ),
        total,
    )


# ============================================================
# Message Persistence
# ============================================================

async def append_message(
    db: AsyncSession,
    session_id: int,
    conversation_id: int,
    user_id: int,
    role: str,
    content: str,

    model_provider: Optional[
        str
    ] = None,

    model_name: Optional[
        str
    ] = None,

    prompt_id: Optional[
        str
    ] = None,

    prompt_version: Optional[
        int
    ] = None,

    citations: Optional[
        list
    ] = None,

    retrieval_metadata: Optional[
        dict
    ] = None,
) -> ResearchMessage:
    """
    向 Conversation 追加 Message。

    使用：

        SELECT ... FOR UPDATE

    锁定 Conversation Row，
    安全分配 sequence_number。
    """

    result = await db.execute(
        select(
            ResearchConversation,
            ResearchSession,
        )
        .join(
            ResearchSession,

            ResearchSession.id
            == ResearchConversation.session_id,
        )
        .where(
            ResearchConversation.id
            == conversation_id,

            ResearchConversation.session_id
            == session_id,

            ResearchSession.owner_id
            == user_id,
        )
        .with_for_update()
    )


    row = (
        result.one_or_none()
    )


    if row is None:

        raise (
            ResearchConversationNotFoundException()
        )


    conversation, session = row


    # ========================================================
    # Sequence Allocation
    # ========================================================

    sequence_number = (
        conversation
        .next_sequence_number
    )


    conversation.next_sequence_number = (
        sequence_number + 1
    )


    # ========================================================
    # Update Activity Time
    # ========================================================

    now = datetime.now(
        timezone.utc
    )


    conversation.updated_at = now

    session.updated_at = now


    # ========================================================
    # Create Message
    # ========================================================

    message = ResearchMessage(
        conversation_id=(
            conversation.id
        ),

        sequence_number=(
            sequence_number
        ),

        role=(
            role
        ),

        content=(
            content
        ),

        model_provider=(
            model_provider
        ),

        model_name=(
            model_name
        ),

        prompt_id=(
            prompt_id
        ),

        prompt_version=(
            prompt_version
        ),

        citations=(
            citations or []
        ),

        retrieval_metadata=(
            retrieval_metadata or {}
        ),
    )


    db.add(
        message
    )


    await db.commit()

    await db.refresh(
        message
    )


    return message


async def list_messages(
    db: AsyncSession,
    session_id: int,
    conversation_id: int,
    user_id: int,
    page: int,
    page_size: int,
) -> tuple[
    list[ResearchMessage],
    int,
]:
    """
    分页读取 Conversation Message。
    """

    await get_owned_conversation(
        db=db,
        session_id=session_id,
        conversation_id=conversation_id,
        user_id=user_id,
    )


    offset = (
        page - 1
    ) * page_size


    count_result = await db.execute(
        select(
            func.count(
                ResearchMessage.id
            )
        ).where(
            ResearchMessage.conversation_id
            == conversation_id
        )
    )


    total = (
        count_result.scalar_one()
    )


    result = await db.execute(
        select(
            ResearchMessage
        )
        .where(
            ResearchMessage.conversation_id
            == conversation_id
        )
        .order_by(
            ResearchMessage
            .sequence_number
        )
        .offset(
            offset
        )
        .limit(
            page_size
        )
    )


    return (
        list(
            result.scalars().all()
        ),
        total,
    )


async def get_recent_history(
    db: AsyncSession,
    conversation_id: int,
    limit: int,
) -> list[
    ResearchMessage
]:
    """
    获取最近 N 条 Conversation Message。

    SQL：

        DESC + LIMIT

    然后 Python：

        reverse()

    恢复正常时间顺序。
    """

    result = await db.execute(
        select(
            ResearchMessage
        )
        .where(
            ResearchMessage.conversation_id
            == conversation_id
        )
        .order_by(
            ResearchMessage
            .sequence_number
            .desc()
        )
        .limit(
            limit
        )
    )


    messages = list(
        result.scalars().all()
    )


    messages.reverse()


    return messages


# ============================================================
# Persistent Conversation RAG
# ============================================================

async def ask_conversation_question(
    db: AsyncSession,
    session_id: int,
    conversation_id: int,
    user_id: int,
    question: str,
    top_k: int,
    use_reranker: bool,
    embedding_provider: EmbeddingProvider,
    llm_provider: LLMProvider,
) -> ConversationTurnResponse:
    """
    一次完整 Conversation Turn。

    Flow：

        Authorization
            ↓
        Load History
            ↓
        Persist User Message
            ↓
        Citation-Aware RAG
            ↓
        Persist Assistant Message
            ↓
        Return Turn
    """

    # ========================================================
    # 1. Conversation Authorization
    # ========================================================

    conversation = (
        await get_owned_conversation(
            db=db,

            session_id=(
                session_id
            ),

            conversation_id=(
                conversation_id
            ),

            user_id=(
                user_id
            ),
        )
    )


    # ========================================================
    # 2. Require Document
    # ========================================================

    if conversation.document is None:

        raise (
            ConversationDocumentRequiredException()
        )


    document_id = (
        conversation.document.id
    )


    paper_id = (
        conversation.document.paper_id
    )


    # ========================================================
    # 3. Reauthorize Document
    # ========================================================

    document = (
        await paper_document
        .get_document(
            db=db,

            paper_id=(
                paper_id
            ),

            document_id=(
                document_id
            ),

            user_id=(
                user_id
            ),
        )
    )


    # ========================================================
    # 4. Load Existing Conversation History
    # ========================================================

    previous_messages = (
        await get_recent_history(
            db=db,

            conversation_id=(
                conversation.id
            ),

            limit=(
                settings
                .CONVERSATION_HISTORY_MESSAGE_LIMIT
            ),
        )
    )


    conversation_history = [
        (
            message.role,
            message.content,
        )

        for message
        in previous_messages

        if message.role
        in {
            "user",
            "assistant",
        }
    ]


    # ========================================================
    # 5. Persist User Message
    # ========================================================

    user_message = (
        await append_message(
            db=db,

            session_id=(
                session_id
            ),

            conversation_id=(
                conversation_id
            ),

            user_id=(
                user_id
            ),

            role="user",

            content=(
                question.strip()
            ),
        )
    )


    # ========================================================
    # 6. RAG Generation
    # ========================================================

    rag_response = (
        await rag_service
        .answer_document_question(
            db=db,

            document=(
                document
            ),

            question=(
                question.strip()
            ),

            top_k=(
                top_k
            ),

            use_reranker=(
                use_reranker
            ),

            embedding_provider=(
                embedding_provider
            ),

            llm_provider=(
                llm_provider
            ),

            conversation_history=(
                conversation_history
            ),
        )
    )


    # ========================================================
    # 7. Citation Payload
    # ========================================================

    citation_payload = [
        citation.model_dump()

        for citation
        in rag_response.citations
    ]


    # ========================================================
    # 8. Retrieval + Prompt Metadata
    # ========================================================

    retrieval_metadata = {
        "grounded":
            rag_response.grounded,

        "retrieval_count":
            rag_response
            .retrieval_count,

        "invalid_citations":
            rag_response
            .invalid_citations,

        # Day32：
        #
        # 同时保存完整 System/User
        # Prompt Provenance。
        "prompt": (
            rag_response
            .prompt
            .model_dump()

            if rag_response.prompt
            is not None

            else None
        ),
    }


    # ========================================================
    # 9. Persist Assistant Message
    # ========================================================

    assistant_message = (
        await append_message(
            db=db,

            session_id=(
                session_id
            ),

            conversation_id=(
                conversation_id
            ),

            user_id=(
                user_id
            ),

            role="assistant",

            content=(
                rag_response.answer
            ),

            # ------------------------------------------------
            # Model Provenance
            # ------------------------------------------------

            model_provider=(
                rag_response
                .model
                .provider

                if rag_response.model
                is not None

                else None
            ),

            model_name=(
                rag_response
                .model
                .model_name

                if rag_response.model
                is not None

                else None
            ),

            # ------------------------------------------------
            # Prompt Provenance
            # ------------------------------------------------

            prompt_id=(
                rag_response
                .prompt
                .user_prompt_id

                if rag_response.prompt
                is not None

                else None
            ),

            prompt_version=(
                rag_response
                .prompt
                .user_prompt_version

                if rag_response.prompt
                is not None

                else None
            ),

            # ------------------------------------------------
            # RAG Metadata
            # ------------------------------------------------

            citations=(
                citation_payload
            ),

            retrieval_metadata=(
                retrieval_metadata
            ),
        )
    )


    # ========================================================
    # 10. Return Turn
    # ========================================================

    return (
        ConversationTurnResponse(
            user_message=(
                user_message
            ),

            assistant_message=(
                assistant_message
            ),

            grounded=(
                rag_response.grounded
            ),

            invalid_citations=(
                rag_response
                .invalid_citations
            ),
        )
    )