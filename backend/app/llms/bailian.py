import logging

import logging

import httpx2

from openai import (
    OpenAI,
)

from backend.app.llms.base import (
    LLMGenerationResult,
    LLMProvider,
)


logger = logging.getLogger(
    __name__
)


class BailianLLMProvider(
    LLMProvider
):
    """
    阿里云百炼 LLM Provider。

    使用 OpenAI-Compatible API。

    当前配置示例：

        Base URL:
        https://dashscope.aliyuncs.com/compatible-mode/v1

        Model:
        qwen3.8-flash

    上层 RAG / Agent 只依赖 LLMProvider，
    不需要知道底层是 Hugging Face
    还是百炼。
    """

    name = "bailian"


    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        max_new_tokens: int,
        temperature: float,
        timeout_seconds: float = 120.0,
        max_retries: int = 2,
    ):
        """
        初始化 Bailian Provider。

        注意：
        API Key 只用于初始化 Client，
        不写日志，不写 Response。
        """

        if not api_key.strip():
            raise ValueError(
                "Bailian API key is required"
            )


        if not base_url.strip():
            raise ValueError(
                "Bailian base URL is required"
            )


        if not model_name.strip():
            raise ValueError(
                "Bailian model name is required"
            )


        self.model_name = (
            model_name.strip()
        )


        self.base_url = (
            base_url.strip()
            .rstrip("/")
        )


        self.max_new_tokens = (
            max_new_tokens
        )


        self.temperature = (
            temperature
        )


        self.timeout_seconds = (
            timeout_seconds
        )


        self.max_retries = (
            max_retries
        )


        # ====================================================
        # OpenAI-Compatible Client
        # ====================================================

        # ============================================================
        # HTTP Client
        # ============================================================
        #
        # trust_env=False：
        #
        # 不自动继承：
        # HTTP_PROXY
        # HTTPS_PROXY
        # ALL_PROXY
        #
        # 避免本机代理软件导致
        # DashScope TLS 握手异常。
        #
        self._http_client = (
            httpx2.Client(
                trust_env=False,

                timeout=(
                    self.timeout_seconds
                ),

                follow_redirects=True,
            )
        )

        # ============================================================
        # OpenAI-Compatible Client
        # ============================================================

        self._client = (
            OpenAI(
                api_key=(
                    api_key
                ),

                base_url=(
                    self.base_url
                ),

                timeout=(
                    self.timeout_seconds
                ),

                max_retries=(
                    self.max_retries
                ),

                http_client=(
                    self._http_client
                ),
            )
        )


    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMGenerationResult:
        """
        调用百炼 OpenAI-Compatible
        Chat Completions API。

        Input:

            System Prompt
            User Prompt

        Output:

            LLMGenerationResult
        """

        # ====================================================
        # Messages
        # ====================================================

        messages = [
            {
                "role": "system",
                "content": (
                    system_prompt
                ),
            },
            {
                "role": "user",
                "content": (
                    user_prompt
                ),
            },
        ]


        logger.debug(
            (
                "Calling Bailian LLM: "
                "model=%s "
                "system_prompt_chars=%d "
                "user_prompt_chars=%d"
            ),
            self.model_name,
            len(system_prompt),
            len(user_prompt),
        )


        # ====================================================
        # API Call
        # ====================================================

        response = (
            self._client
            .chat
            .completions
            .create(
                model=(
                    self.model_name
                ),

                messages=(
                    messages
                ),

                temperature=(
                    self.temperature
                ),

                max_tokens=(
                    self.max_new_tokens
                ),
            )
        )


        # ====================================================
        # Validate Response
        # ====================================================

        if not response.choices:

            raise RuntimeError(
                "Bailian returned no choices"
            )


        message = (
            response
            .choices[0]
            .message
        )


        text = (
            message.content
            or ""
        ).strip()


        if not text:

            raise RuntimeError(
                "Bailian returned an empty response"
            )


        logger.debug(
            (
                "Bailian LLM response received: "
                "model=%s output_chars=%d"
            ),
            self.model_name,
            len(text),
        )


        # ====================================================
        # Unified Result
        # ====================================================

        return (
            LLMGenerationResult(
                text=(
                    text
                ),

                provider=(
                    self.name
                ),

                model_name=(
                    self.model_name
                ),
            )
        )


    def get_model_name(
        self,
    ) -> str:
        """
        返回当前百炼模型名称。
        """

        return self.model_name