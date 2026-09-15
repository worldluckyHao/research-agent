from abc import ABC, abstractmethod
from dataclasses import dataclass


# ============================================================
# Internal Exceptions
# ============================================================

class EmbeddingInputTooLongError(
    ValueError
):
    """
    输入超过 Embedding Model
    支持的最大 Token 长度。
    """

    def __init__(
        self,
        actual_tokens: int,
        max_tokens: int,
    ):
        self.actual_tokens = (
            actual_tokens
        )

        self.max_tokens = (
            max_tokens
        )

        super().__init__(
            (
                "Embedding input is too long: "
                f"{actual_tokens} > "
                f"{max_tokens}"
            )
        )


class EmbeddingDimensionMismatchError(
    RuntimeError
):
    """
    模型真实 Dimension
    与系统配置不一致。
    """

    def __init__(
        self,
        actual_dimension: int,
        expected_dimension: int,
    ):
        self.actual_dimension = (
            actual_dimension
        )

        self.expected_dimension = (
            expected_dimension
        )

        super().__init__(
            (
                "Embedding dimension mismatch: "
                f"{actual_dimension} != "
                f"{expected_dimension}"
            )
        )


# ============================================================
# Value Objects
# ============================================================

@dataclass(frozen=True)
class EmbeddingBatch:
    """
    一批 Embedding 的结果。
    """

    vectors: list[
        list[float]
    ]

    provider: str

    model_name: str

    dimension: int

    normalized: bool

    device: str


# ============================================================
# Provider Interface
# ============================================================

class EmbeddingProvider(ABC):
    """
    Embedding Provider（向量模型提供者）
    的统一抽象。

    关键设计：

    Documents 和 Query
    使用独立方法。

    Future:
        SentenceTransformer
        OpenAI
        BGE
        Cohere
    """

    name: str


    @abstractmethod
    def embed_documents(
        self,
        texts: list[str],
    ) -> EmbeddingBatch:
        """
        对需要进入知识库的 Document Text
        生成向量。
        """


    @abstractmethod
    def embed_query(
        self,
        text: str,
    ) -> EmbeddingBatch:
        """
        对用户 Query 生成向量。
        """


    @abstractmethod
    def get_dimension(
        self,
    ) -> int:
        """返回 Embedding Dimension。"""


    @abstractmethod
    def get_model_name(
        self,
    ) -> str:
        """返回模型名称。"""


    @abstractmethod
    def get_device(
        self,
    ) -> str:
        """返回模型实际运行设备。"""