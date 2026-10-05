from typing import (
    Callable,
)

import pytest

from backend.app.llms.base import (
    LLMGenerationResult,
    LLMProvider,
)


# ============================================================
# Fake LLM Provider
# ============================================================

class FakeLLMProvider(
    LLMProvider
):
    """
    测试专用 LLM Provider。

    不访问：
        Bailian
        HuggingFace
        Internet

    generate() 永远返回预设文本。

    这样 Unit Test：
        快
        稳定
        免费
        可重复
    """

    name = "fake"


    def __init__(
        self,
        response_text: str,
    ):
        self._response_text = (
            response_text
        )


    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMGenerationResult:
        """
        忽略真实 Prompt 内容，
        返回测试预设结果。
        """

        return (
            LLMGenerationResult(
                text=(
                    self._response_text
                ),

                provider=(
                    self.name
                ),

                model_name=(
                    self.get_model_name()
                ),
            )
        )


    def get_model_name(
        self,
    ) -> str:
        return "fake-test-model"


# ============================================================
# Fixture
# ============================================================

@pytest.fixture
def fake_llm_provider_factory(
) -> Callable[
    [str],
    LLMProvider,
]:
    """
    Factory Fixture。

    Test 中可以：

        provider = fake_llm_provider_factory(
            '{"score": 1.0}'
        )
    """

    def _factory(
        response_text: str,
    ) -> LLMProvider:

        return (
            FakeLLMProvider(
                response_text=(
                    response_text
                )
            )
        )


    return _factory