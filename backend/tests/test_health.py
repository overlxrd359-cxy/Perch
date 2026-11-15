"""M0 验收：健康检查、请求 ID、统一错误响应。"""

from __future__ import annotations

import httpx
import pytest

from app.api.v1.endpoints import health


async def test_healthz_returns_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert response.headers["x-request-id"]


async def test_request_id_from_upstream_is_reused(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz", headers={"X-Request-ID": "trace-abc-123"})

    assert response.headers["x-request-id"] == "trace-abc-123"


async def test_suspicious_request_id_is_replaced(client: httpx.AsyncClient) -> None:
    """超长/非法字符的上游 request id 不能原样回显（防日志注入）。"""
    response = await client.get("/healthz", headers={"X-Request-ID": "x" * 80})

    assert response.headers["x-request-id"] != "x" * 80
    assert len(response.headers["x-request-id"]) == 32


async def test_readyz_ok_when_dependencies_are_up(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def ok() -> None:
        return None

    monkeypatch.setattr(health, "_check_database", ok)
    monkeypatch.setattr(health, "_check_redis", ok)

    response = await client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"mysql": True, "redis": True}}


async def test_readyz_returns_503_when_dependencies_are_down(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail() -> None:
        raise ConnectionError("dependency down")

    monkeypatch.setattr(health, "_check_database", fail)
    monkeypatch.setattr(health, "_check_redis", fail)

    response = await client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"] == {"mysql": False, "redis": False}
    assert body["errors"]["mysql"].startswith("ConnectionError")


async def test_unknown_route_uses_unified_error_shape(client: httpx.AsyncClient) -> None:
    response = await client.get("/no-such-endpoint")

    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"code", "message", "request_id"}
    assert body["code"] == "not_found"
    assert body["request_id"] == response.headers["x-request-id"]
