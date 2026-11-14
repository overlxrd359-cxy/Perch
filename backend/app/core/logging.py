"""结构化日志。

全部输出 JSON，方便后续被 Loki / ELK 采集。
禁止使用 print，业务代码统一 `logging.getLogger(__name__)`。
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# 请求上下文：由中间件写入，日志自动带上
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="-")

# 允许直接挂到 LogRecord 上的额外字段（白名单，防止把密码打进日志）
_EXTRA_FIELDS = ("method", "path", "status", "duration_ms", "client_ip")

_configured = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }

        user_id = user_id_ctx.get()
        if user_id != "-":
            payload["user_id"] = user_id

        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def setup_logging(level: str = "INFO") -> None:
    """初始化根日志器。幂等，重复调用不会叠加 handler。"""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # 第三方库降噪
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore", "redis.asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True
