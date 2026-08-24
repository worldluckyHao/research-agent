import hashlib
import json
from typing import Any, Optional

import redis.asyncio as redis


class CacheService:
    """
    Redis Cache Service。

    负责：
    1. Cache Key 生成
    2. JSON 序列化
    3. Redis GET
    4. Redis SET
    5. TTL
    """

    def __init__(
        self,
        redis_client: redis.Redis,
    ):
        self.redis = redis_client


    @staticmethod
    def build_key(
        namespace: str,
        payload: dict[str, Any],
    ) -> str:
        """
        根据请求参数生成稳定 Cache Key。
        """

        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        digest = hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

        return (
            f"research-agent:"
            f"{namespace}:"
            f"{digest}"
        )


    async def get_json(
        self,
        key: str,
    ) -> Optional[dict]:
        """
        从 Redis 获取 JSON 数据。
        """

        value = await self.redis.get(
            key
        )

        if value is None:
            return None

        return json.loads(
            value
        )


    async def set_json(
        self,
        key: str,
        value: dict,
        ttl_seconds: int,
    ) -> None:
        """
        写入 JSON Cache，并设置 TTL。
        """

        serialized = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        await self.redis.set(
            key,
            serialized,
            ex=ttl_seconds,
        )


    async def delete(
        self,
        key: str,
    ) -> None:
        """
        删除指定缓存。
        """

        await self.redis.delete(
            key
        )