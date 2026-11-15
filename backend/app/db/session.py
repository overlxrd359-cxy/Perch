"""数据库引擎与会话。

- 引擎在 import 时只创建对象，**不建立连接**：MySQL 没起时进程也能启动，
  `/readyz` 负责报告依赖不可用，而不是让启动直接崩掉。
- pool_pre_ping 防 MySQL 空闲断连；pool_recycle 要小于 MySQL 的 wait_timeout。
- 事务边界在 service 层，get_session 只负责“一个请求一个 session + 异常回滚”。
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

engine = create_async_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=10,
    echo=False,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：正常路径由 service 决定 commit，异常路径统一回滚。"""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
