import html
import re
from datetime import date
from typing import Optional

from backend.app.clients.crossref import (
    CrossrefClient,
)
from backend.app.providers.base import (
    PaperProvider,
)
from backend.app.schemas.external import (
    PaperSearchSort,
    UnifiedPaperMetadata,
    UnifiedPaperSearchResponse,
)


class CrossrefProvider(PaperProvider):
    """
    Crossref -> UnifiedPaperMetadata Adapter。
    """

    name = "crossref"


    SORT_MAP = {
        PaperSearchSort.RELEVANCE: "score",
        PaperSearchSort.NEWEST: "published",
        PaperSearchSort.CITED: (
            "is-referenced-by-count"
        ),
    }


    def __init__(
        self,
        client: CrossrefClient,
    ):
        self.client = client


    @staticmethod
    def _extract_title(
        work: dict,
    ) -> str:
        titles = work.get(
            "title",
            [],
        )

        if titles:
            return titles[0].strip()

        return "Untitled"


    @staticmethod
    def _extract_authors(
        work: dict,
    ) -> list[str]:
        authors = []

        for author in work.get(
            "author",
            [],
        ):
            given = (
                author.get("given")
                or ""
            )

            family = (
                author.get("family")
                or ""
            )

            name = (
                f"{given} {family}"
            ).strip()

            if name:
                authors.append(name)

        return authors


    @staticmethod
    def _extract_year(
        work: dict,
    ) -> Optional[int]:
        published = (
            work.get("published")
            or {}
        )

        date_parts = (
            published.get("date-parts")
            or []
        )

        if (
            date_parts
            and date_parts[0]
        ):
            year = date_parts[0][0]

            if isinstance(year, int):
                return year

        return None


    @staticmethod
    def _extract_publication_date(
        work: dict,
    ) -> Optional[date]:
        published = (
            work.get("published")
            or {}
        )

        date_parts = (
            published.get("date-parts")
            or []
        )

        if not date_parts:
            return None

        values = date_parts[0]

        try:
            if len(values) >= 3:
                return date(
                    values[0],
                    values[1],
                    values[2],
                )

            if len(values) == 2:
                return date(
                    values[0],
                    values[1],
                    1,
                )

            if len(values) == 1:
                return date(
                    values[0],
                    1,
                    1,
                )

        except (ValueError, TypeError):
            return None

        return None


    @staticmethod
    def _clean_abstract(
        value: Optional[str],
    ) -> Optional[str]:
        """
        Crossref abstract 有时包含 JATS/XML tags，
        转换成适合内部使用的普通文本。
        """

        if not value:
            return None

        text = re.sub(
            r"<[^>]+>",
            " ",
            value,
        )

        text = html.unescape(text)

        text = " ".join(
            text.split()
        )

        return text or None


    @staticmethod
    def _extract_venue(
        work: dict,
    ) -> Optional[str]:
        values = work.get(
            "container-title",
            [],
        )

        if values:
            return values[0]

        return None


    def _normalize_work(
        self,
        work: dict,
    ) -> UnifiedPaperMetadata:
        doi = work.get("DOI")

        provider_id = (
            doi
            or work.get("URL")
            or self._extract_title(work)
        )


        return UnifiedPaperMetadata(
            provider=self.name,

            provider_id=provider_id,

            sources=[
                self.name
            ],

            provider_ids={
                self.name: provider_id
            },

            title=self._extract_title(
                work
            ),

            authors=self._extract_authors(
                work
            ),

            abstract=self._clean_abstract(
                work.get("abstract")
            ),

            year=self._extract_year(
                work
            ),

            publication_date=(
                self._extract_publication_date(
                    work
                )
            ),

            doi=doi,

            url=work.get("URL"),

            venue=self._extract_venue(
                work
            ),

            cited_by_count=(
                work.get(
                    "is-referenced-by-count"
                )
                or 0
            ),

            language=work.get(
                "language"
            ),

            topics=[
                subject
                for subject in work.get(
                    "subject",
                    [],
                )
                if subject
            ],
        )


    async def search(
        self,
        query: str,
        page: int,
        page_size: int,
        sort: PaperSearchSort,
    ) -> UnifiedPaperSearchResponse:

        offset = (
            page - 1
        ) * page_size


        raw_data = await self.client.search_works(
            query=query,
            offset=offset,
            rows=page_size,
            sort=self.SORT_MAP[sort],
        )


        items_data = (
            raw_data.get("items")
            or []
        )

        total = (
            raw_data.get("total-results")
            or 0
        )


        items = [
            self._normalize_work(work)
            for work in items_data
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

        work = await self.client.get_work_by_doi(
            doi=identifier
        )

        return self._normalize_work(
            work
        )