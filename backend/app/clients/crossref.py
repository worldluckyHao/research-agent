import logging
from urllib.parse import quote

import httpx

from backend.app.core.config import settings
from backend.app.core.exceptions import (
    ExternalResourceNotFoundException,
    ExternalServiceResponseException,
    ExternalServiceTimeoutException,
    ExternalServiceUnavailableException,
)


logger = logging.getLogger(__name__)


class CrossrefClient:
    """
    Crossref REST API Client。

    这里只负责：
    - HTTP 请求
    - HTTP 错误转换
    - 返回原始 Crossref 数据

    不负责业务字段清洗。
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
    ):
        self.client = client

        self.base_url = (
            settings.CROSSREF_BASE_URL.rstrip("/")
        )


    async def get_work_by_doi(
        self,
        doi: str,
    ) -> dict:
        """
        根据 DOI 查询 Crossref Work。
        """

        # DOI 可能包含 "/"，需要安全编码后放进 URL。
        encoded_doi = quote(
            doi.strip(),
            safe="",
        )

        url = (
            f"{self.base_url}/works/{encoded_doi}"
        )

        headers = {
            "User-Agent": settings.CROSSREF_USER_AGENT,
            "Accept": "application/json",
        }

        try:
            response = await self.client.get(
                url,
                headers=headers,
            )

        except httpx.TimeoutException as exc:
            logger.warning(
                "Crossref request timeout: doi=%s",
                doi,
            )

            raise ExternalServiceTimeoutException() from exc

        except httpx.RequestError as exc:
            logger.exception(
                "Crossref network error: doi=%s",
                doi,
            )

            raise ExternalServiceUnavailableException() from exc


        # Crossref 中没有该 DOI。
        if response.status_code == 404:
            raise ExternalResourceNotFoundException()


        # 429 表示第三方服务正在限流。
        if response.status_code == 429:
            logger.warning(
                "Crossref rate limited request"
            )

            raise ExternalServiceUnavailableException()


        # 其他 4xx / 5xx。
        if response.is_error:
            logger.error(
                "Crossref error: status=%s",
                response.status_code,
            )

            raise ExternalServiceUnavailableException()


        try:
            data = response.json()

        except ValueError as exc:
            raise ExternalServiceResponseException() from exc


        # Crossref 正常结构应该包含 message。
        message = data.get("message")

        if not isinstance(message, dict):
            raise ExternalServiceResponseException()

        return message