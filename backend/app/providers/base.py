from abc import (
    ABC,
    abstractmethod,
)

from backend.app.schemas.external import (
    PaperSearchSort,
    UnifiedPaperMetadata,
    UnifiedPaperSearchResponse,
)


class PaperProvider(ABC):
    """
    所有学术论文数据源 Provider 的统一接口。

    上层业务只依赖 PaperProvider，
    不直接依赖 OpenAlex / arXiv / Crossref。
    """

    name: str


    @abstractmethod
    async def search(
        self,
        query: str,
        page: int,
        page_size: int,
        sort: PaperSearchSort,
    ) -> UnifiedPaperSearchResponse:
        """
        搜索论文。
        """

        raise NotImplementedError


    @abstractmethod
    async def get(
        self,
        identifier: str,
    ) -> UnifiedPaperMetadata:
        """
        根据 Provider 支持的 identifier 获取论文。
        """

        raise NotImplementedError