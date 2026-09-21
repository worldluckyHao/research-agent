from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMGenerationResult:
    """
    LLM 单次生成结果。
    """

    text: str

    provider: str

    model_name: str


class LLMProvider(ABC):
    """
    LLM Provider（大语言模型提供者）
    的统一接口。
    """

    name: str


    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMGenerationResult:
        """
        根据 System Prompt + User Prompt
        生成回答。
        """


    @abstractmethod
    def get_model_name(
        self,
    ) -> str:
        """返回当前模型名称。"""