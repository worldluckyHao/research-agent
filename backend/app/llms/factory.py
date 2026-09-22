from typing import (
    Optional,
)
import logging
from backend.app.core.config import (
    settings,
)
from backend.app.llms.base import (
    LLMProvider,
)
from backend.app.llms.bailian import (
    BailianLLMProvider,
)
from backend.app.llms.huggingface import (
    HuggingFaceLLMProvider,
)

logger = logging.getLogger(__name__)
# ============================================================
# Process-Level Provider Cache
# ============================================================

_llm_provider: Optional[
    LLMProvider
] = None


# ============================================================
# Factory
# ============================================================

def create_llm_provider(
) -> LLMProvider:
    """
    创建并缓存当前 LLM Provider。

    Supported:

        huggingface
        bailian

    Provider 在当前 FastAPI Process
    内只创建一次。

    切换 Provider 后需要重启应用。
    """

    global _llm_provider
    logger.warning(
        "LLM FACTORY: configured_provider=%s configured_model=%s cached_provider=%s",
        settings.LLM_PROVIDER,
        settings.LLM_MODEL_NAME,
        (
            type(_llm_provider).__name__
            if _llm_provider is not None
            else "None"
        ),
    )

    # ========================================================
    # Return Cached Provider
    # ========================================================

    if _llm_provider is not None:
        return (
            _llm_provider
        )

    # ========================================================
    # Hugging Face
    # ========================================================

    if (
        settings.LLM_PROVIDER
        == "huggingface"
    ):

        _llm_provider = (
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


        return (
            _llm_provider
        )


    # ========================================================
    # Alibaba Cloud Bailian
    # ========================================================

    if (
        settings.LLM_PROVIDER
        == "bailian"
    ):

        # ----------------------------------------------------
        # Validate API Key
        # ----------------------------------------------------

        if (
            settings.BAILIAN_API_KEY
            is None
        ):

            raise RuntimeError(
                (
                    "BAILIAN_API_KEY is required "
                    "when LLM_PROVIDER=bailian"
                )
            )


        api_key = (
            settings
            .BAILIAN_API_KEY
            .get_secret_value()
            .strip()
        )


        if not api_key:

            raise RuntimeError(
                (
                    "BAILIAN_API_KEY is empty "
                    "when LLM_PROVIDER=bailian"
                )
            )


        # ----------------------------------------------------
        # Validate Base URL
        # ----------------------------------------------------

        base_url = (
            settings
            .BAILIAN_BASE_URL
            .strip()
        )


        if not base_url:

            raise RuntimeError(
                (
                    "BAILIAN_BASE_URL is required "
                    "when LLM_PROVIDER=bailian"
                )
            )


        # ----------------------------------------------------
        # Create Provider
        # ----------------------------------------------------

        _llm_provider = (
            BailianLLMProvider(
                api_key=(
                    api_key
                ),

                base_url=(
                    base_url
                ),

                model_name=(
                    settings
                    .LLM_MODEL_NAME
                ),

                max_new_tokens=(
                    settings
                    .LLM_MAX_NEW_TOKENS
                ),

                temperature=(
                    settings
                    .LLM_TEMPERATURE
                ),

                timeout_seconds=(
                    settings
                    .BAILIAN_TIMEOUT_SECONDS
                ),

                max_retries=(
                    settings
                    .BAILIAN_MAX_RETRIES
                ),
            )
        )


        return (
            _llm_provider
        )


    # ========================================================
    # Unsupported
    # ========================================================

    raise RuntimeError(
        (
            "Unsupported LLM provider: "
            f"{settings.LLM_PROVIDER}"
        )
    )