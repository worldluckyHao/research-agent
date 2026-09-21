from functools import lru_cache

from backend.app.core.config import (
    settings,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.llms.huggingface import (
    HuggingFaceLLMProvider,
)


@lru_cache(
    maxsize=1
)
def create_llm_provider(
) -> LLMProvider:
    """
    每个进程缓存一个 LLM Provider。

    避免每次 Request
    重新加载模型。
    """

    if (
        settings.LLM_PROVIDER
        == "huggingface"
    ):

        return (
            HuggingFaceLLMProvider(
                model_name=(
                    settings
                    .LLM_MODEL_NAME
                ),

                device=(
                    settings
                    .LLM_DEVICE
                ),

                max_new_tokens=(
                    settings
                    .LLM_MAX_NEW_TOKENS
                ),

                temperature=(
                    settings
                    .LLM_TEMPERATURE
                ),

                do_sample=(
                    settings
                    .LLM_DO_SAMPLE
                ),
            )
        )


    raise RuntimeError(
        (
            "Unsupported LLM provider: "
            f"{settings.LLM_PROVIDER}"
        )
    )