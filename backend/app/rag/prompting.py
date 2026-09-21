from dataclasses import dataclass
from typing import Optional

from backend.app.core.config import (
    settings,
)
from backend.app.prompts.rag import (
    RAG_SYSTEM_PROMPT_ID,
    RAG_USER_PROMPT_ID,
)
from backend.app.prompts.registry import (
    prompt_registry,
)


# ============================================================
# Render Result
# ============================================================

@dataclass(frozen=True)
class RenderedRAGPrompts:
    """
    Prompt Rendering Result
    （RAG提示词渲染结果）。

    不仅保存最终 Prompt Text，
    同时保留 Prompt Provenance。
    """

    system_prompt: str

    user_prompt: str

    system_prompt_id: str

    system_prompt_version: int

    user_prompt_id: str

    user_prompt_version: int


# ============================================================
# Conversation History
# ============================================================

def format_conversation_history(
    conversation_history: Optional[
        list[
            tuple[str, str]
        ]
    ],
) -> str:
    """
    将 Conversation History
    转换成 Prompt Text。

    重要原则：

    History：
        只帮助模型理解上下文和指代。

    Evidence：
        才是真正事实依据。
    """

    if not conversation_history:

        return ""


    blocks = []


    for role, content in conversation_history:

        if role == "user":

            role_name = "User"

        elif role == "assistant":

            role_name = "Assistant"

        else:

            # 当前 RAG Prompt
            # 只注入 user / assistant。
            continue


        blocks.append(
            f"{role_name}:\n"
            f"{content}"
        )


    return "\n\n".join(
        blocks
    )


# ============================================================
# Prompt Rendering
# ============================================================

def render_rag_prompts(
    question: str,
    context: str,
    conversation_history: Optional[
        list[
            tuple[str, str]
        ]
    ] = None,
) -> RenderedRAGPrompts:
    """
    根据 Day32 Prompt Registry
    渲染当前版本的 RAG Prompt。

    LangGraph / LangChain / 原生 Service
    都复用这一套逻辑。
    """

    # --------------------------------------------------------
    # Conversation History
    # --------------------------------------------------------

    history_text = (
        format_conversation_history(
            conversation_history
        )
    )


    if history_text:

        history_section = (
            "Conversation History:\n"
            f"{history_text}\n\n"
        )

    else:

        history_section = ""


    # --------------------------------------------------------
    # Active Prompt Versions
    # --------------------------------------------------------

    system_version = (
        settings
        .RAG_SYSTEM_PROMPT_VERSION
    )


    user_version = (
        settings
        .RAG_USER_PROMPT_VERSION
    )


    # --------------------------------------------------------
    # System Prompt
    # --------------------------------------------------------

    system_prompt = (
        prompt_registry.render(
            prompt_id=(
                RAG_SYSTEM_PROMPT_ID
            ),

            version=(
                system_version
            ),
        )
    )


    # --------------------------------------------------------
    # User Prompt
    # --------------------------------------------------------

    user_prompt = (
        prompt_registry.render(
            prompt_id=(
                RAG_USER_PROMPT_ID
            ),

            version=(
                user_version
            ),

            history_section=(
                history_section
            ),

            question=(
                question
            ),

            context=(
                context
            ),
        )
    )


    return RenderedRAGPrompts(
        system_prompt=(
            system_prompt
        ),

        user_prompt=(
            user_prompt
        ),

        system_prompt_id=(
            RAG_SYSTEM_PROMPT_ID
        ),

        system_prompt_version=(
            system_version
        ),

        user_prompt_id=(
            RAG_USER_PROMPT_ID
        ),

        user_prompt_version=(
            user_version
        ),
    )