import redis.asyncio as redis

from backend.app.core.config import settings


def create_redis_client() -> redis.Redis:
    """
    创建应用级异步 Redis Client。

    decode_responses=True：
    Redis 返回 str，而不是 bytes。
    """

    return redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )