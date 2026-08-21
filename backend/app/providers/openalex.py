from datetime import date
from typing import Optional

from backend.app.clients.openalex import (
    OpenAlexClient,
)
from backend.app.providers.base import (
    PaperProvider,
)
from backend.app.schemas.external import (
    PaperSearchSort,
    UnifiedPaperMetadata,
    UnifiedPaperSearchResponse,
)


class OpenAlexProvider(PaperProvider):
    """
    OpenAlex -> Research Agent Provider。

    职责：
    1. 调用 OpenAlexClient；
    2. 将 OpenAlex 数据转换成统一 Paper Metadata。
    """

    name = "openalex"


    SORT_MAP = {
        PaperSearchSort.RELEVANCE: (
            "relevance_score:desc"
        ),

        PaperSearchSort.NEWEST: (
            "publication_date:desc"
        ),

        PaperSearchSort.CITED: (
            "cited_by_count:desc"
        ),
    }


    def __init__(
        self,
        client: OpenAlexClient,
    ):
        self.client = client


    @staticmethod
    def _extract_openalex_id(
        value: Optional[str],
    ) -> str:
        """
        https://openalex.org/W2741809807
        ↓
        W2741809807
        """

        if not value:
            return ""

        return value.rstrip("/").split("/")[-1]


    @staticmethod
    def _normalize_doi(
        doi: Optional[str],
    ) -> Optional[str]:
        """
        OpenAlex DOI 常见格式：

        https://doi.org/10.xxxx/xxxx

        Research Agent 内部统一成：

        10.xxxx/xxxx
        """

        if not doi:
            return None

        prefix = "https://doi.org/"

        if doi.lower().startswith(prefix):
            return doi[len(prefix):]

        return doi


    @staticmethod
    def _reconstruct_abstract(
        inverted_index: Optional[
            dict[str, list[int]]
        ],
    ) -> Optional[str]:
        """
        OpenAlex Abstract 不是普通字符串，
        而是 inverted index：

        {
            "Deep": [0],
            "learning": [1, 10],
            ...
        }

        这里根据 token position 重建原始文本。
        """

        if not inverted_index:
            return None


        positioned_words = []

        for word, positions in (
            inverted_index.items()
        ):
            for position in positions:
                positioned_words.append(
                    (
                        position,
                        word,
                    )
                )


        positioned_words.sort(
            key=lambda item: item[0]
        )


        abstract = " ".join(
            word
            for _, word
            in positioned_words
        )


        return abstract or None


    @staticmethod
    def _extract_authors(
        work: dict,
    ) -> list[str]:
        """
        从 OpenAlex authorships 中提取作者姓名。
        """

        authors = []

        for authorship in work.get(
            "authorships",
            [],
        ):
            author = authorship.get(
                "author"
            ) or {}

            name = author.get(
                "display_name"
            )

            if name:
                authors.append(name)


        return authors


    @staticmethod
    def _extract_venue(
        work: dict,
    ) -> Optional[str]:
        """
        优先从 primary_location 获取期刊/会议来源。
        """

        primary_location = (
            work.get("primary_location")
            or {}
        )

        source = (
            primary_location.get("source")
            or {}
        )

        return source.get(
            "display_name"
        )


    @staticmethod
    def _extract_url(
        work: dict,
    ) -> Optional[str]:
        """
        获取主要论文页面 URL。
        """

        primary_location = (
            work.get("primary_location")
            or {}
        )

        return (
            primary_location.get(
                "landing_page_url"
            )
            or work.get("doi")
            or work.get("id")
        )


    @staticmethod
    def _extract_pdf_url(
        work: dict,
    ) -> Optional[str]:
        """
        优先获取 Open Access PDF。
        """

        best_oa_location = (
            work.get("best_oa_location")
            or {}
        )

        return best_oa_location.get(
            "pdf_url"
        )


    @staticmethod
    def _extract_topics(
        work: dict,
    ) -> list[str]:
        """
        提取 OpenAlex Topic 名称。
        """

        topics = []

        for topic in work.get(
            "topics",
            [],
        ):
            name = topic.get(
                "display_name"
            )

            if name:
                topics.append(name)


        return topics


    @staticmethod
    def _parse_publication_date(
        value: Optional[str],
    ) -> Optional[date]:
        """
        将 YYYY-MM-DD 转成 Python date。
        """

        if not value:
            return None

        try:
            return date.fromisoformat(
                value
            )

        except ValueError:
            return None


    def _normalize_work(
        self,
        work: dict,
    ) -> UnifiedPaperMetadata:
        """
        OpenAlex Work
        ↓
        UnifiedPaperMetadata
        """

        open_access = (
            work.get("open_access")
            or {}
        )

        openalex_id = self._extract_openalex_id(
            work.get("id")
        )

        return UnifiedPaperMetadata(
            provider=self.name,

            provider_id=(
                self._extract_openalex_id(
                    work.get("id")
                )
            ),
            sources=[
                self.name
            ],

            provider_ids={
                self.name: self._extract_openalex_id(
                    work.get("id")
                )
            },
            title=(
                work.get("display_name")
                or "Untitled"
            ),

            authors=(
                self._extract_authors(
                    work
                )
            ),

            abstract=(
                self._reconstruct_abstract(
                    work.get(
                        "abstract_inverted_index"
                    )
                )
            ),

            year=work.get(
                "publication_year"
            ),

            publication_date=(
                self._parse_publication_date(
                    work.get(
                        "publication_date"
                    )
                )
            ),

            doi=(
                self._normalize_doi(
                    work.get("doi")
                )
            ),

            url=self._extract_url(
                work
            ),

            pdf_url=self._extract_pdf_url(
                work
            ),

            venue=self._extract_venue(
                work
            ),

            cited_by_count=(
                work.get(
                    "cited_by_count"
                )
                or 0
            ),

            is_open_access=(
                open_access.get(
                    "is_oa"
                )
            ),

            language=work.get(
                "language"
            ),

            topics=self._extract_topics(
                work
            ),
        )


    async def search(
        self,
        query: str,
        page: int,
        page_size: int,
        sort: PaperSearchSort,
    ) -> UnifiedPaperSearchResponse:
        """
        统一论文搜索接口。
        """

        raw_data = await self.client.search_works(
            query=query,
            page=page,
            per_page=page_size,
            sort=self.SORT_MAP[sort],
        )


        meta = (
            raw_data.get("meta")
            or {}
        )

        results = (
            raw_data.get("results")
            or []
        )


        total = (
            meta.get("count")
            or 0
        )


        pages = (
            (total + page_size - 1)
            // page_size
            if total > 0
            else 0
        )


        items = [
            self._normalize_work(work)
            for work in results
        ]


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
        """
        根据 OpenAlex ID / DOI 获取论文。
        """

        work = await self.client.get_work(
            identifier=identifier
        )

        return self._normalize_work(
            work
        )