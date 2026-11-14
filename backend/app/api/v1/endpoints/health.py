"""健康检查。

- /healthz：存活探针，只表明进程活着，不碰外部依赖。
- /readyz ：就绪探针，检查 MySQL / Redis，任一不可用返回 503。

两者语义必须分开：数据库挂了，进程是活的（不该被重启），
但不应该继续接流量（该被摘除）。
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.core.config import settings
from app.core.redis import ping_redis
from app.db.session import engine

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="存活检查")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version, "env": settings.env}


@router.get("/readyz", summary="就绪检查")
async def readyz(response: Response) -> dict[str, Any]:
    checks: dict[str, str] = {}
    healthy = True

    try:
        await asyncio.wait_for(ping_redis(), timeout=2.0)
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "down"
        healthy = False

    try:
        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=2.0)
        checks["mysql"] = "ok"
    except Exception:
        checks["mysql"] = "down"
        healthy = False

    if not healthy:
        response.status_code = 503

    return {"status": "ok" if healthy else "degraded", "checks": checks}
