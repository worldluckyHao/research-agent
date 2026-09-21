from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


# ============================================================
# Research Session
# ============================================================

class ResearchSessionCreate(
    BaseModel
):
    """
    创建一个 Research Session。
    """

    title: str = Field(
        min_length=1,
        max_length=200,
    )


class ResearchSessionResponse(
    BaseModel
):
    """
    Research Session Response。
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    owner_id: int

    title: str

    created_at: datetime

    updated_at: datetime


class ResearchSessionListResponse(
    BaseModel
):
    """
    Session 分页响应。
    """

    items: list[
        ResearchSessionResponse
    ]

    total: int

    page: int

    page_size: int


# ============================================================
# Research Conversation
# ============================================================

class ResearchConversationCreate(
    BaseModel
):
    """
    创建 Conversation。

    paper_id / document_id：

        要么同时提供；
        要么同时为空。
    """

    title: str = Field(
        default="New conversation",
        min_length=1,
        max_length=200,
    )

    paper_id: Optional[int] = None

    document_id: Optional[int] = None


    @model_validator(
        mode="after"
    )
    def validate_document_pair(
        self,
    ):
        """
        paper_id 和 document_id
        必须同时存在或同时为空。
        """

        has_paper = (
            self.paper_id
            is not None
        )

        has_document = (
            self.document_id
            is not None
        )


        if has_paper != has_document:

            raise ValueError(
                (
                    "paper_id and document_id "
                    "must be provided together"
                )
            )


        return self


class ResearchConversationResponse(
    BaseModel
):
    """
    Conversation Response。
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    session_id: int

    document_id: Optional[int] = None

    title: str

    next_sequence_number: int

    created_at: datetime

    updated_at: datetime


class ResearchConversationListResponse(
    BaseModel
):
    """
    Conversation 分页结果。
    """

    items: list[
        ResearchConversationResponse
    ]

    total: int

    page: int

    page_size: int


# ============================================================
# Research Message
# ============================================================

class ResearchMessageResponse(
    BaseModel
):
    """
    Research Message Response。

    Day32 新增：

        prompt_id
        prompt_version
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    conversation_id: int

    sequence_number: int

    role: str

    content: str


    # --------------------------------------------------------
    # Model Provenance
    # --------------------------------------------------------

    model_provider: Optional[
        str
    ] = None

    model_name: Optional[
        str
    ] = None


    # --------------------------------------------------------
    # Prompt Provenance
    # --------------------------------------------------------

    prompt_id: Optional[
        str
    ] = None

    prompt_version: Optional[
        int
    ] = None


    # --------------------------------------------------------
    # RAG Metadata
    # --------------------------------------------------------

    citations: list

    retrieval_metadata: dict


    created_at: datetime


class ResearchMessageListResponse(
    BaseModel
):
    """
    Conversation Message 分页响应。
    """

    items: list[
        ResearchMessageResponse
    ]

    total: int

    page: int

    page_size: int


# ============================================================
# Conversation Ask
# ============================================================

class ConversationAskRequest(
    BaseModel
):
    """
    Persistent Conversation RAG 请求。
    """

    question: str = Field(
        min_length=2,
        max_length=4000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )

    use_reranker: bool = True


class ConversationTurnResponse(
    BaseModel
):
    """
    一次完整 User -> Assistant Turn。
    """

    user_message: (
        ResearchMessageResponse
    )

    assistant_message: (
        ResearchMessageResponse
    )

    grounded: bool

    invalid_citations: list[str]