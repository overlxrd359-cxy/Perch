"""ORM 基类与公共 Mixin。

约定：时间统一存 UTC 的 DATETIME（naive），展示层再用 core.time 转换。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.time import utcnow


class Base(DeclarativeBase):
    """所有模型的声明式基类；Alembic 的 target_metadata 指向 Base.metadata。"""


class IntPKMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
