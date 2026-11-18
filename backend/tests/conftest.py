"""pytest 全局 fixtures。

顺序要求：**先设置环境变量，再 import app**。Settings 是导入期校验，
CI 环境没有 .env，顺序反了整个测试收集阶段直接失败。

数据库策略：
- 使用独立的 `campus_seat_test` 库，绝不碰开发库
- 测试库地址优先取 `TEST_DATABASE_URL`；否则读项目根 `.env` 的 DATABASE_URL 并换库名
- 每个用例建表 → 跑 → 删表，保证互不影响
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TEST_DATABASE_NAME = "campus_seat_test"


def _read_env_file(key: str) -> str | None:
    env_file = _PROJECT_ROOT / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return None


def _with_database(url: str, database: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{database}"))


def _test_database_url() -> str:
    """优先显式 TEST_DATABASE_URL，其次项目 .env（避开 shell 里残留的变量）。"""
    base = (
        os.environ.get("TEST_DATABASE_URL")
        or _read_env_file("DATABASE_URL")
        or "mysql+asyncmy://seat:seat_dev_pwd@127.0.0.1:3306/campus_seat?charset=utf8mb4"
    )
    return _with_database(base, _TEST_DATABASE_NAME)


# 直接覆盖而不 setdefault：外部 shell 里可能残留 .env 的 APP_ENV=dev，setdefault 挡不住
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef0123456789abcdef"
os.environ["DATABASE_URL"] = _test_database_url()
# 用 15 号库，避免测试误碰开发缓存；测试里验证码走内存存储
os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/15"

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db import init_models  # noqa: F401  # 触发模型注册
from app.db.base import Base
from app.db.session import engine
from app.main import create_app
from app.services import verification

TEST_DATABASE_URL = os.environ["DATABASE_URL"]
_db_ready = False


async def _ensure_database() -> None:
    """测试库不存在时尝试创建；已存在则直接复用。

    本地开发用的 `seat` 账号通常没有 CREATE DATABASE 权限，所以先探测，
    探测失败才尝试创建，创建也失败就给出可操作的提示。
    """
    global _db_ready
    if _db_ready:
        return

    probe_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    try:
        async with probe_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        admin_engine = create_async_engine(
            _with_database(TEST_DATABASE_URL, ""),
            poolclass=NullPool,
            isolation_level="AUTOCOMMIT",
        )
        try:
            async with admin_engine.connect() as connection:
                await connection.execute(
                    text(
                        f"CREATE DATABASE IF NOT EXISTS {_TEST_DATABASE_NAME} "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                )
        finally:
            await admin_engine.dispose()
    finally:
        await probe_engine.dispose()
    _db_ready = True


@pytest.fixture
async def db_schema() -> AsyncIterator[None]:
    """建表 → 用例 → 删表。"""
    await _ensure_database()
    schema_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with schema_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        async with schema_engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await schema_engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_state() -> AsyncIterator[None]:
    """每个用例重置验证码存储，并释放全局连接池（避免跨事件循环复用连接）。"""
    verification.reset_code_store()
    yield
    await engine.dispose()


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    """进程内 ASGI 客户端，不走网络端口。"""
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """直连测试库，用来断言落库结果。"""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
def captured_codes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """拦截"发邮件"，把验证码留在内存里给测试用。"""
    sent: list[tuple[str, str]] = []

    def fake_send(email: str, code: str) -> None:
        sent.append((email, code))

    monkeypatch.setattr(verification, "send_verification_email", fake_send)
    return sent
