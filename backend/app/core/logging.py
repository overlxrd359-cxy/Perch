"""结构化日志。

- 每行一条 JSON，字段固定：ts / level / logger / msg / request_id
- request_id 走 ContextVar，业务代码不需要手动传参
- 额外字段走白名单，**绝不打印请求体**（防密码、token 进日志）
- 第三方库降噪，避免 SQLAlchemy / uvicorn 把日志刷成噪音
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
user_id_ctx: ContextVar[int | None] = ContextVar("user_id", default=None)

# 允许透传到日志的额外字段。想加字段先加到白名单，别随手 extra 塞任意对象。
_EXTRA_WHITELIST = frozenset(
    {"method", "path", "status", "duration_ms", "user_id", "seat_id", "reservation_id"}
)

# 第三方库降噪：这些库的 DEBUG 日志会把正常请求淹掉
_NOISY_LOGGERS: dict[str, int] = {
    "asyncio": logging.INFO,
    "uvicorn.access": logging.WARNING,
    "sqlalchemy.engine": logging.WARNING,
    "sqlalchemy.pool": logging.WARNING,
    "alembic": logging.WARNING,
    "httpx": logging.WARNING,
    "httpcore": logging.WARNING,
    "redis": logging.WARNING,
    "asyncmy": logging.WARNING,
}

_configured = False


class JsonFormatter(logging.Formatter):
    """把 LogRecord 序列化成单行 JSON。"""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }

        context_user = user_id_ctx.get()
        if context_user is not None:
            payload["user_id"] = context_user

        for key in _EXTRA_WHITELIST:
            if key in record.__dict__ and key not in payload:
                payload[key] = record.__dict__[key]

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(*, level: str | int = "INFO", json_output: bool = True) -> None:
    """初始化根 logger。重复调用无副作用（--reload 会重复 import）。"""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter()
        if json_output
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for name, noisy_level in _NOISY_LOGGERS.items():
        logging.getLogger(name).setLevel(noisy_level)

    _configured = True
