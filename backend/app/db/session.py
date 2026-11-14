"""数据库会话与引擎。

- 引擎在导入时创建，但不会立刻建立连接（SQLAlchemy 懒连接）。
- pool_pre_ping 防止 MySQL 8 小时空闲断连导致的 "MySQL server has gone away"。
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    echo=False,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：每个请求一个 session，退出时自动关闭。"""
    async with SessionLocal() as session:
        yield session
