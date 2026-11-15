"""pytest 全局 fixtures。

**必须在 import app 之前设置环境变量**：CI 环境没有 .env，
Settings 是导入期校验，缺 SECRET_KEY 会让整个测试收集阶段直接失败。

M1 起在这里加数据库 fixture（事务回滚隔离）。
"""

from __future__ import annotations

import os

# 直接覆盖而不 setdefault：外部 shell 里可能残留 .env 的 APP_ENV=dev，setdefault 挡不住
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef0123456789abcdef"
os.environ["DATABASE_URL"] = (
    "mysql+asyncmy://seat:seat_dev_pwd@127.0.0.1:3306/campus_seat?charset=utf8mb4"
)
# 用 15 号库，避免测试误碰开发数据
os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/15"

from collections.abc import AsyncIterator

import httpx
import pytest

from app.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """进程内 ASGI 客户端，不走网络端口。"""
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
