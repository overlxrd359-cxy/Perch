"""时间统一入口。

规则（全项目唯一，M3 的 slot 计算也依赖它）：
- 入库一律 naive UTC：MySQL DATETIME 不带时区，带 tzinfo 写库会被驱动告警或截断。
- 对外展示、日志用带时区时间。
- 业务代码禁止裸 ``datetime.now()``，所有转换只在本模块发生。
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def now_utc() -> datetime:
    """当前时间，带 UTC 时区。日志 / 对外接口用这个。"""
    return datetime.now(UTC)


def utcnow() -> datetime:
    """当前 UTC 时间，naive。用于 DATETIME 列默认值。"""
    return now_utc().replace(tzinfo=None)


def to_naive_utc(value: datetime) -> datetime:
    """任意时间转 naive UTC。naive 输入按 UTC 解释。"""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def to_local(value: datetime) -> datetime:
    """naive UTC / aware 时间 → 本地时区（Asia/Shanghai）的带时区时间。"""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(LOCAL_TZ)


def from_local(value: datetime) -> datetime:
    """本地时间（可 naive）→ naive UTC。用于把用户输入转成入库值。"""
    if value.tzinfo is None:
        value = value.replace(tzinfo=LOCAL_TZ)
    return value.astimezone(UTC).replace(tzinfo=None)
