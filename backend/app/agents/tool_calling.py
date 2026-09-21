import json
from dataclasses import dataclass
from typing import Any

from backend.app.core.config import (
    settings,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.prompts.registry import (
    prompt_registry,
)
from backend.app.prompts.tool_calling import (
    TOOL_SELECTION_SYSTEM_PROMPT_ID,
    TOOL_SELECTION_USER_PROMPT_ID,
)
from backend.app.rag.generation import (
    generate_rag_answer,
)
from backend.app.tools.registry import (
    ToolRegistry,
)


# ============================================================
# Decision
# ============================================================

@dataclass(frozen=True)
class ToolCallDecision:
    """
    Tool Call Decision（工具调用决策）。

    action:
        call_tool
        no_tool
    """

    action: str

    tool_name: str | None

    query: str

    reason: str


# ============================================================
# JSON Helper
# ============================================================

def _parse_json_object(
    text: str,
) -> dict[str, Any]:
    """
    解析 Tool Selector JSON。
    """

    cleaned = (
        text.strip()
    )


    if cleaned.startswith(
        "```"
    ):

        lines = (
            cleaned.splitlines()
        )


        if lines:

            lines = lines[1:]


        if (
            lines
            and lines[-1]
            .strip()
            .startswith("```")
        ):

            lines = lines[:-1]


        cleaned = (
            "\n".join(
                lines
            )
            .strip()
        )


    try:

        payload = json.loads(
            cleaned
        )


        if not isinstance(
            payload,
            dict,
        ):

            raise ValueError(
                "Expected JSON object"
            )


        return payload


    except (
        json.JSONDecodeError,
        ValueError,
    ):

        pass


    start = cleaned.find(
        "{"
    )

    end = cleaned.rfind(
        "}"
    )


    if (
        start == -1
        or end == -1
        or end <= start
    ):

        raise ValueError(
            "Tool selector returned no JSON object"
        )


    payload = json.loads(
        cleaned[
            start:
            end + 1
        ]
    )


    if not isinstance(
        payload,
        dict,
    ):

        raise ValueError(
            "Expected JSON object"
        )


    return payload


# ============================================================
# Tool Catalog
# ============================================================

def _format_tool_catalog(
    registry: ToolRegistry,
) -> str:
    """
    将 Tool Registry 转换成
    LLM 可读取的 JSON Catalog。
    """

    return json.dumps(
        registry.specifications(),
        ensure_ascii=False,
        indent=2,
    )


# ============================================================
# Tool Selection
# ============================================================

async def select_research_tool(
    llm_provider: LLMProvider,
    registry: ToolRegistry,
    question: str,
    retrieval_query: str,
    tool_feedback: str = "(none)",
) -> ToolCallDecision:
    """
    使用 LLM 选择下一 Tool。

    非常重要：

    LLM 只负责建议：
        tool_name

    后端最终还会：
        registry.get(tool_name)

    所以模型无法调用未注册 Tool。
    """

    system_prompt = (
        prompt_registry.render(
            prompt_id=(
                TOOL_SELECTION_SYSTEM_PROMPT_ID
            ),

            version=(
                settings
                .TOOL_SELECTION_PROMPT_VERSION
            ),
        )
    )


    user_prompt = (
        prompt_registry.render(
            prompt_id=(
                TOOL_SELECTION_USER_PROMPT_ID
            ),

            version=(
                settings
                .TOOL_SELECTION_PROMPT_VERSION
            ),

            question=(
                question
            ),

            retrieval_query=(
                retrieval_query
            ),

            tool_catalog=(
                _format_tool_catalog(
                    registry
                )
            ),

            tool_feedback=(
                tool_feedback
            ),
        )
    )


    generation = (
        await generate_rag_answer(
            llm_provider=(
                llm_provider
            ),

            system_prompt=(
                system_prompt
            ),

            user_prompt=(
                user_prompt
            ),
        )
    )


    try:

        payload = (
            _parse_json_object(
                generation.text
            )
        )


        action = str(
            payload.get(
                "action",
                "no_tool",
            )
        ).strip()


        reason = str(
            payload.get(
                "reason",
                "",
            )
        ).strip()


        query = str(
            payload.get(
                "query",
                retrieval_query,
            )
        ).strip()


        raw_tool_name = (
            payload.get(
                "tool_name"
            )
        )


        tool_name = (
            str(
                raw_tool_name
            ).strip()

            if raw_tool_name
            is not None

            else None
        )


        # ====================================================
        # Validate Action
        # ====================================================

        if action != "call_tool":

            return ToolCallDecision(
                action="no_tool",
                tool_name=None,
                query="",
                reason=(
                    reason
                    or (
                        "No suitable tool "
                        "was selected."
                    )
                ),
            )


        # ====================================================
        # Validate Tool
        # ====================================================

        if not tool_name:

            return ToolCallDecision(
                action="no_tool",
                tool_name=None,
                query="",
                reason=(
                    "Tool selector did not "
                    "provide a tool name."
                ),
            )


        # Registry validation.
        #
        # Unknown tool:
        # registry.get() raises ValueError.
        registry.get(
            tool_name
        )


        if not query:

            query = (
                retrieval_query
            )


        return ToolCallDecision(
            action="call_tool",

            tool_name=(
                tool_name
            ),

            query=(
                query
            ),

            reason=(
                reason
                or "Tool selected."
            ),
        )


    except (
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):

        # ====================================================
        # Graceful Fallback
        # ====================================================
        #
        # 当前 Registry 如果只有本地检索 Tool，
        # Selector JSON 失败时可以安全回退到它。
        tools = (
            registry.list_tools()
        )


        if len(tools) == 1:

            tool = tools[0]


            return ToolCallDecision(
                action="call_tool",

                tool_name=(
                    tool.name
                ),

                query=(
                    retrieval_query
                ),

                reason=(
                    "Tool selection output "
                    "could not be parsed; "
                    "single-tool fallback used."
                ),
            )


        return ToolCallDecision(
            action="no_tool",

            tool_name=None,

            query="",

            reason=(
                "Tool selection output "
                "could not be parsed."
            ),
        )