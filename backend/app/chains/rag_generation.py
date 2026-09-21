from dataclasses import dataclass
from typing import Any

from langchain_core.messages import (
    BaseMessage,
)
from langchain_core.prompts import (
    ChatPromptTemplate,
)
from langchain_core.runnables import (
    Runnable,
    RunnableLambda,
)

from backend.app.llms.base import (
    LLMGenerationResult,
    LLMProvider,
)


# ============================================================
# Chain Result
# ============================================================

@dataclass(frozen=True)
class RAGChainResult:
    """
    LangChain RAG Generation Result
    （LangChain RAG生成结果）。

    为什么不只返回 str？

    因为 Research-Agent 不只需要文本，
    还需要：

        provider
        model_name

    用于：
        Message Provenance
        Debug
        Evaluation
    """

    text: str

    provider: str

    model_name: str


# ============================================================
# Prompt
# ============================================================

def create_chat_prompt(
) -> ChatPromptTemplate:
    """
    创建 ChatPromptTemplate（聊天提示词模板）。

    注意：

    Prompt Registry 已经负责：
        Prompt ID
        Version
        Variable Render

    所以这里 LangChain 不再重复管理
    Prompt Version。

    它只负责把已经 Render 好的：

        system_prompt
        user_prompt

    转换为标准 Chat Messages。
    """

    return (
        ChatPromptTemplate
        .from_messages(
            [
                (
                    "system",
                    "{system_prompt}",
                ),
                (
                    "human",
                    "{user_prompt}",
                ),
            ]
        )
    )


# ============================================================
# PromptValue -> Provider Input
# ============================================================

def _extract_system_and_user(
    prompt_value: Any,
) -> tuple[
    str,
    str,
]:
    """
    把 LangChain PromptValue
    转回我们自定义 LLMProvider 需要的：

        system_prompt
        user_prompt

    为什么需要这一步？

    因为当前 LLMProvider 接口是：

        generate(
            system_prompt,
            user_prompt,
        )

    而 ChatPromptTemplate 输出的是：

        ChatPromptValue
            ↓
        BaseMessage[]

    这就是 Adapter（适配）过程。
    """

    messages: list[
        BaseMessage
    ] = (
        prompt_value
        .to_messages()
    )


    system_parts = []

    user_parts = []


    for message in messages:

        message_type = (
            message.type
        )


        if message_type == "system":

            system_parts.append(
                str(
                    message.content
                )
            )


        elif message_type in {
            "human",
            "user",
        }:

            user_parts.append(
                str(
                    message.content
                )
            )


    if not system_parts:

        raise RuntimeError(
            (
                "LangChain RAG prompt "
                "contains no system message"
            )
        )


    if not user_parts:

        raise RuntimeError(
            (
                "LangChain RAG prompt "
                "contains no user message"
            )
        )


    system_prompt = (
        "\n\n".join(
            system_parts
        )
    )


    user_prompt = (
        "\n\n".join(
            user_parts
        )
    )


    return (
        system_prompt,
        user_prompt,
    )


# ============================================================
# LLMProvider Adapter
# ============================================================

def _create_provider_runnable(
    llm_provider: LLMProvider,
) -> Runnable:
    """
    将 Research-Agent 自定义的
    LLMProvider 适配成 LangChain Runnable。

    原有接口：

        LLMProvider.generate(
            system_prompt,
            user_prompt,
        )

    LangChain 需要：

        Input
          ↓
        Runnable
          ↓
        Output

    所以使用 RunnableLambda
    包一层 Adapter。
    """

    def invoke_provider(
        prompt_value: Any,
    ) -> LLMGenerationResult:
        """
        同步调用 Provider。

        LangChain 的 ainvoke()
        会负责把同步 RunnableLambda
        放到合适的异步执行路径中。
        """

        (
            system_prompt,
            user_prompt,
        ) = _extract_system_and_user(
            prompt_value
        )


        return (
            llm_provider.generate(
                system_prompt=(
                    system_prompt
                ),

                user_prompt=(
                    user_prompt
                ),
            )
        )


    return RunnableLambda(
        invoke_provider
    )


# ============================================================
# Output Adapter
# ============================================================

def _convert_generation_result(
    generation: LLMGenerationResult,
) -> RAGChainResult:
    """
    将底层 Provider Result
    转换为 Chain Result。

    这里单独做一层的原因：

    LangChain Pipeline 上层不应该依赖
    某个具体 Provider 的内部实现。
    """

    return RAGChainResult(
        text=(
            generation.text
        ),

        provider=(
            generation.provider
        ),

        model_name=(
            generation.model_name
        ),
    )


# ============================================================
# Chain Factory
# ============================================================

def create_rag_generation_chain(
    llm_provider: LLMProvider,
) -> Runnable:
    """
    创建 Day33 的 LCEL RAG Generation Chain。

    Pipeline：

        dict
          ↓
        ChatPromptTemplate
          ↓
        LLMProvider Adapter
          ↓
        Result Adapter
          ↓
        RAGChainResult

    对应 LCEL：

        prompt
        | provider
        | result_parser
    """

    prompt = (
        create_chat_prompt()
    )


    provider_runnable = (
        _create_provider_runnable(
            llm_provider
        )
    )


    result_runnable = (
        RunnableLambda(
            _convert_generation_result
        )
    )


    chain = (
        prompt
        | provider_runnable
        | result_runnable
    )


    return chain