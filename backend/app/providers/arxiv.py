from backend.app.clients.arxiv import (
    ArxivClient,
)
from backend.app.parsers.arxiv import (
    parse_arxiv_feed,
)
from backend.app.providers.base import (
    PaperProvider,
)
from backend.app.schemas.external import (
    PaperSearchSort,
    UnifiedPaperMetadata,
    UnifiedPaperSearchResponse,
)


class ArxivProvider(PaperProvider):
    """
    arXiv -> UnifiedPaperMetadata Adapter。
    """

    name = "arxiv"


    SORT_MAP = {
        PaperSearchSort.RELEVANCE: (
            "relevance"
        ),

        PaperSearchSort.NEWEST: (
            "submittedDate"
        ),

        # arXiv 本身没有 citation count。
        # 多源聚合后 CITED 会根据其他 Provider
        # 补充的 cited_by_count 重新排序。
        PaperSearchSort.CITED: (
            "relevance"
        ),
    }


    def __init__(
        self,
        client: ArxivClient,
    ):
        self.client = client


    @staticmethod
    def _strip_arxiv_version(
        arxiv_id: str,
    ) -> str:
        """
        1706.03762v7
        ↓
        1706.03762

        去重时版本号通常不应该让同一篇论文
        被视为两个不同实体。
        """

        import re

        return re.sub(
            r"v\d+$",
            "",
            arxiv_id,
        )


    def _normalize_item(
        self,
        item: dict,
    ) -> UnifiedPaperMetadata:

        raw_arxiv_id = item[
            "arxiv_id"
        ]

        arxiv_id = (
            self._strip_arxiv_version(
                raw_arxiv_id
            )
        )


        return UnifiedPaperMetadata(
            provider=self.name,

            provider_id=arxiv_id,

            sources=[
                self.name
            ],

            provider_ids={
                self.name: arxiv_id
            },

            title=item["title"],

            authors=item[
                "authors"
            ],

            abstract=item.get(
                "abstract"
            ),

            year=item.get(
                "year"
            ),

            publication_date=(
                item["published_at"].date()
                if item.get("published_at")
                else None
            ),

            doi=item.get(
                "doi"
            ),

            arxiv_id=arxiv_id,

            url=item.get(
                "abstract_url"
            ),

            pdf_url=item.get(
                "pdf_url"
            ),

            topics=item.get(
                "categories",
                [],
            ),
        )


    async def search(
        self,
        query: str,
        page: int,
        page_size: int,
        sort: PaperSearchSort,
    ) -> UnifiedPaperSearchResponse:

        start = (
            page - 1
        ) * page_size


        xml_text = await self.client.search(
            search_query=(
                f'all:"{query}"'
            ),

            start=start,

            max_results=page_size,

            sort_by=(
                self.SORT_MAP[sort]
            ),

            sort_order="descending",
        )


        parsed = parse_arxiv_feed(
            xml_text
        )


        total = parsed[
            "total"
        ]


        items = [
            self._normalize_item(item)
            for item in parsed["items"]
        ]


        pages = (
            (total + page_size - 1)
            // page_size
            if total > 0
            else 0
        )


        return UnifiedPaperSearchResponse(
            provider=self.name,
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )


    async def get(
        self,
        identifier: str,
    ) -> UnifiedPaperMetadata:

        xml_text = await self.client.get_by_id(
            arxiv_id=identifier
        )

        parsed = parse_arxiv_feed(
            xml_text
        )


        if not parsed["items"]:
            from backend.app.core.exceptions import (
                ExternalResourceNotFoundException,
            )

            raise ExternalResourceNotFoundException()


        return self._normalize_item(
            parsed["items"][0]
        )