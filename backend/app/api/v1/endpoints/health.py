"""健康检查端点。

语义必须分开，混在一起会让编排系统做出错误决策：

- ``/healthz``：存活探针。只看进程是否活着，**不碰任何外部依赖**。
  数据库挂了也不能让容器被重启——问题不在这个进程。
- ``/readyz``：就绪探针。并发探测 MySQL / Redis，任一不可用返回 503。
  放在根路径（不在 /api/v1 下），生产 healthcheck 与 Caddy 都按根路径探活。
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.core.config import get_settings
from app.core.redis import ping_redis
from app.db.session import engine

router = APIRouter(tags=["health"])

# 单次依赖探测超时：2 秒足够本地 / 内网，超时按“不可用”处理
PROBE_TIMEOUT_SECONDS = 2.0


async def _check_database() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def _check_redis() -> None:
    await ping_redis()


async def _probe(name: str, probe: Awaitable[None]) -> tuple[str, bool, str | None]:
    try:
        await asyncio.wait_for(probe, timeout=PROBE_TIMEOUT_SECONDS)
    except Exception as exc:  # 探测失败原因要原样返回给运维
        return name, False, f"{type(exc).__name__}: {exc}"[:200]
    return name, True, None


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version, "env": settings.app_env}


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, Any]:
    results = await asyncio.gather(
        _probe("mysql", _check_database()),
        _probe("redis", _check_redis()),
    )
    checks = {name: ok for name, ok, _ in results}
    errors = {name: error for name, ok, error in results if not ok and error}

    healthy = all(checks.values())
    if not healthy:
        response.status_code = 503
        response.headers["Cache-Control"] = "no-store"

    payload: dict[str, Any] = {
        "status": "ok" if healthy else "degraded",
        "checks": checks,
    }
    if errors:
        payload["errors"] = errors
    return payload
