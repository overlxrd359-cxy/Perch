"""健康检查与基础设施冒烟测试。

这些测试不依赖 MySQL / Redis，用于保证服务本身能起来。
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_healthz_returns_ok(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert resp.status_code == 200

    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["env"] == "test"


async def test_request_id_is_echoed(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert resp.headers.get("X-Request-ID")


async def test_request_id_is_reused_from_header(client: AsyncClient) -> None:
    resp = await client.get("/healthz", headers={"X-Request-ID": "trace-abc-123"})
    assert resp.headers["X-Request-ID"] == "trace-abc-123"


async def test_api_ping(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/ping")
    assert resp.status_code == 200
    assert resp.json() == {"pong": "ok"}


async def test_readyz_reports_degraded_without_deps(client: AsyncClient) -> None:
    """没有启动 MySQL / Redis 时，readyz 应该返回 503 而不是崩溃。"""
    resp = await client.get("/readyz")
    assert resp.status_code == 503

    body = resp.json()
    assert body["status"] == "degraded"
    assert body["checks"]["redis"] in {"ok", "down"}
    assert body["checks"]["mysql"] in {"ok", "down"}


async def test_unknown_route_returns_404(client: AsyncClient) -> None:
    resp = await client.get("/definitely-not-here")
    assert resp.status_code == 404
