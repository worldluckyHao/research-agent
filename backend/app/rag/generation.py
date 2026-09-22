import asyncio

from backend.app.chains.rag_generation import (
    RAGChainResult,
    create_rag_generation_chain,
)
from backend.app.core.config import (
    settings,
)
from backend.app.llms.base import (
    LLMGenerationResult,
    LLMProvider,
)
from backend.app.observability.langsmith import (
    observed_async,
)

# ============================================================
# Native Generation
# ============================================================

async def _generate_with_native_engine(
    llm_provider: LLMProvider,
    system_prompt: str,
    user_prompt: str,
) -> RAGChainResult:
    """
    Day30 原生 LLM Generation。

    使用 asyncio.to_thread()
    避免同步模型推理阻塞 FastAPI Event Loop。
    """

    generation: LLMGenerationResult = (
        await asyncio.to_thread(
            llm_provider.generate,

            system_prompt,

            user_prompt,
        )
    )


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
# LangChain Generation
# ============================================================

async def _generate_with_langchain_engine(
    llm_provider: LLMProvider,
    system_prompt: str,
    user_prompt: str,
) -> RAGChainResult:
    """
    Day33 LangChain LCEL Generation。
    """

    chain = (
        create_rag_generation_chain(
            llm_provider=(
                llm_provider
            )
        )
    )


    result = (
        await chain.ainvoke(
            {
                "system_prompt":
                    system_prompt,

                "user_prompt":
                    user_prompt,
            }
        )
    )


    if not isinstance(
        result,
        RAGChainResult,
    ):

        raise RuntimeError(
            (
                "LangChain RAG chain "
                "returned an invalid result"
            )
        )


    return result

@observed_async(
    name="llm.rag_generation",
    run_type="llm",
    tags=[
        "llm",
        "generation",
    ],
)

# ============================================================
# Generation Router
# ============================================================

async def generate_rag_answer(
    llm_provider: LLMProvider,
    system_prompt: str,
    user_prompt: str,
) -> RAGChainResult:
    """
    统一 Generation Entry。

    根据配置：

        native
        或
        langchain

    选择实际 Generation Engine。

    LangGraph 不需要知道底层
    到底是原生调用还是 LCEL。
    """

    engine = (
        settings
        .RAG_GENERATION_ENGINE
    )


    if engine == "native":

        return (
            await _generate_with_native_engine(
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


    if engine == "langchain":

        return (
            await _generate_with_langchain_engine(
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


    raise RuntimeError(
        (
            "Unsupported RAG generation "
            f"engine: {engine}"
        )
    )