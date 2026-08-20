import asyncio
import logging
import time

import httpx

from backend.app.core.config import settings
from backend.app.core.exceptions import (
    ExternalServiceResponseException,
    ExternalServiceTimeoutException,
    ExternalServiceUnavailableException,
)


logger = logging.getLogger(__name__)


class ArxivClient:
    """
    arXiv HTTP Client。

    职责：
    1. 构造 arXiv API 请求；
    2. 控制请求频率；
    3. 处理网络异常；
    4. 返回 Atom XML 文本。

    XML 解析不放在 Client 中，
    交给独立 Parser 负责。
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
    ):
        self.client = client

        self.api_url = settings.ARXIV_API_URL

        self.min_request_interval = (
            settings.ARXIV_MIN_REQUEST_INTERVAL_SECONDS
        )

        # 控制并发请求进入 arXiv。
        self._request_lock = asyncio.Lock()

        # 记录上一次请求完成时间。
        self._last_request_finished_at = 0.0


    async def _wait_for_rate_limit(
        self,
    ) -> None:
        """
        保证连续 arXiv 请求之间存在最小时间间隔。

        注意：
        必须在 _request_lock 内调用。
        """

        now = time.monotonic()

        elapsed = (
            now
            - self._last_request_finished_at
        )

        remaining = (
            self.min_request_interval
            - elapsed
        )

        if remaining > 0:
            await asyncio.sleep(remaining)


    async def _request(
        self,
        params: dict,
    ) -> str:
        """
        执行一次受限流保护的 arXiv 请求。
        """

        # 整个 arXiv Client 串行控制请求间隔。
        async with self._request_lock:

            await self._wait_for_rate_limit()

            try:
                response = await self.client.get(
                    self.api_url,
                    params=params,
                    headers={
                        "Accept": "application/atom+xml",
                    },
                )

            except httpx.TimeoutException as exc:
                logger.warning(
                    "arXiv request timeout: type=%s",
                    type(exc).__name__,
                )

                raise ExternalServiceTimeoutException() from exc

            except httpx.RequestError as exc:
                logger.exception(
                    "arXiv network request failed"
                )

                raise ExternalServiceUnavailableException() from exc

            finally:
                # monotonic() 不受系统时间调整影响，
                # 适合计算请求间隔。
                self._last_request_finished_at = (
                    time.monotonic()
                )


        if response.is_error:
            logger.error(
                "arXiv API error: status=%s",
                response.status_code,
            )

            raise ExternalServiceUnavailableException()


        # arXiv 正常返回 Atom/XML。
        content_type = response.headers.get(
            "content-type",
            "",
        )

        if (
            "xml" not in content_type.lower()
            and "atom" not in content_type.lower()
        ):
            logger.warning(
                "Unexpected arXiv response type: %s",
                content_type,
            )

            raise ExternalServiceResponseException()


        return response.text


    async def search(
        self,
        search_query: str,
        start: int,
        max_results: int,
        sort_by: str,
        sort_order: str,
    ) -> str:
        """
        根据 arXiv search_query 搜索论文。
        """

        params = {
            "search_query": search_query,
            "start": start,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        return await self._request(
            params=params
        )


    async def get_by_id(
        self,
        arxiv_id: str,
    ) -> str:
        """
        根据 arXiv ID 精确查询论文。

        官方 API 推荐这种场景使用 id_list。
        """

        params = {
            "id_list": arxiv_id,
            "start": 0,
            "max_results": 1,
        }

        return await self._request(
            params=params
        )