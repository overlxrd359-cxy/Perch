"""Redis 客户端。

- 单例懒加载：import 本模块不发连接、不 ping，`/readyz` 才知道依赖是否可用
- 后续用途：座位图缓存、分布式锁、令牌桶限流、ZSET 延迟任务
"""

from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    """返回进程内单例。"""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis


async def ping_redis() -> bool:
    return bool(await get_redis().ping())


async def close_redis() -> None:
    """关闭连接池。lifespan 退出时调用。"""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
