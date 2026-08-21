import logging
from typing import Any, Optional
from urllib.parse import quote

import httpx

from backend.app.core.config import settings
from backend.app.core.exceptions import (
    ExternalResourceNotFoundException,
    ExternalServiceRateLimitedException,
    ExternalServiceResponseException,
    ExternalServiceTimeoutException,
    ExternalServiceUnavailableException,
)


logger = logging.getLogger(__name__)


class OpenAlexClient:
    """
    OpenAlex REST API Client。

    Client 层只负责：
    1. 构造 HTTP 请求；
    2. Authentication；
    3. HTTP / Network Error 转换；
    4. 返回 OpenAlex 原始 JSON。

    不负责把 OpenAlex 数据转换成
    Research Agent 的统一 Paper Model。
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
    ):
        self.client = client

        self.base_url = (
            settings.OPENALEX_BASE_URL.rstrip("/")
        )


    def _build_headers(
        self,
    ) -> dict[str, str]:
        """
        构造请求 Header。

        如果配置了 API Key，
        使用 Authorization Header，
        避免 Key 出现在 URL 中。
        """

        headers = {
            "Accept": "application/json",
        }

        if settings.OPENALEX_API_KEY is not None:
            api_key = (
                settings.OPENALEX_API_KEY
                .get_secret_value()
                .strip()
            )

            if api_key:
                headers["Authorization"] = (
                    f"Bearer {api_key}"
                )

        return headers


    async def _request(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict:
        """
        OpenAlex 通用 GET 请求。

        所有 OpenAlex API 方法最终都经过这里，
        因此异常处理逻辑不会散落到各个方法中。
        """

        url = (
            f"{self.base_url}/{path.lstrip('/')}"
        )

        try:
            response = await self.client.get(
                url,
                params=params,
                headers=self._build_headers(),
            )

        except httpx.TimeoutException as exc:
            logger.warning(
                "OpenAlex request timeout: "
                "type=%s url=%s",
                type(exc).__name__,
                url,
            )

            raise ExternalServiceTimeoutException() from exc

        except httpx.RequestError as exc:
            logger.exception(
                "OpenAlex network request failed: "
                "url=%s",
                url,
            )

            raise ExternalServiceUnavailableException() from exc


        if response.status_code == 404:
            raise ExternalResourceNotFoundException()


        if response.status_code == 429:
            logger.warning(
                "OpenAlex rate limited request: url=%s",
                url,
            )

            raise ExternalServiceRateLimitedException()


        if response.status_code >= 500:
            logger.error(
                "OpenAlex upstream error: "
                "status=%s url=%s",
                response.status_code,
                url,
            )

            raise ExternalServiceUnavailableException()


        if response.status_code >= 400:
            logger.error(
                "OpenAlex invalid request response: "
                "status=%s body=%s",
                response.status_code,
                response.text[:500],
            )

            raise ExternalServiceResponseException()


        try:
            data = response.json()

        except ValueError as exc:
            logger.exception(
                "OpenAlex returned invalid JSON"
            )

            raise ExternalServiceResponseException() from exc


        if not isinstance(data, dict):
            raise ExternalServiceResponseException()


        return data


    async def search_works(
        self,
        query: str,
        page: int,
        per_page: int,
        sort: str,
    ) -> dict:
        """
        搜索 OpenAlex Works。
        """

        # 只获取 Research Agent 当前真正需要的字段。
        # 减少响应大小和不必要的数据解析。
        selected_fields = ",".join(
            [
                "id",
                "doi",
                "display_name",
                "publication_year",
                "publication_date",
                "authorships",
                "abstract_inverted_index",
                "primary_location",
                "best_oa_location",
                "open_access",
                "cited_by_count",
                "type",
                "language",
                "topics",
                "ids",
            ]
        )

        params = {
            "search": query,
            "page": page,
            "per_page": per_page,
            "sort": sort,
            "select": selected_fields,
        }

        return await self._request(
            path="works",
            params=params,
        )


    async def get_work(
        self,
        identifier: str,
    ) -> dict:
        """
        根据 OpenAlex ID 或外部 ID 查询 Work。

        支持示例：
        W2741809807
        doi:10.xxxx/xxxx
        """

        normalized_identifier = (
            identifier.strip()
        )

        # DOI 中可能包含 "/"，
        # 放在 URL path 前必须编码。
        encoded_identifier = quote(
            normalized_identifier,
            safe=":",
        )

        selected_fields = ",".join(
            [
                "id",
                "doi",
                "display_name",
                "publication_year",
                "publication_date",
                "authorships",
                "abstract_inverted_index",
                "primary_location",
                "best_oa_location",
                "open_access",
                "cited_by_count",
                "type",
                "language",
                "topics",
                "ids",
            ]
        )

        return await self._request(
            path=f"works/{encoded_identifier}",
            params={
                "select": selected_fields,
            },
        )