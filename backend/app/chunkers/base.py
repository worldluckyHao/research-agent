from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkInputPage:
    """
    Chunker 的输入 Page。

    Chunker 不直接依赖 SQLAlchemy ORM。
    """

    page_number: int

    text: str


@dataclass(frozen=True)
class ChunkResult:
    """
    单个 Chunk 的生成结果。
    """

    chunk_index: int

    content: str

    start_page: int

    end_page: int

    token_count: int

    content_sha256: str


class DocumentChunker(ABC):
    """
    Text Chunker（文本分块器）统一抽象。

    Future:
        TokenWindowChunker
        SemanticChunker
        SectionAwareChunker
    """

    name: str

    version: str


    @abstractmethod
    def chunk(
        self,
        pages: list[ChunkInputPage],
    ) -> list[ChunkResult]:
        """
        将 Page Text 转换成多个 Chunk。
        """