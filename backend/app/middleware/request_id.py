"""请求 ID 与访问日志中间件。

- 复用上游 X-Request-ID，没有就生成；上游值做长度与字符校验，防日志注入
- 写入 ContextVar，异常路径也保证 reset（否则同线程复用会串 ID）
- 响应头回传 X-Request-ID
- 记一条访问日志：method / path / status / duration_ms

注册顺序：本中间件必须**最后** add，才会处在最外层，包住 CORS 与异常处理。
"""

from __future__ import annotations

import logging
import re
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_ctx

logger = logging.getLogger("app.access")

# 只接受 1–64 位的安全字符，其余一律丢弃重新生成（防 CRLF / 超长头）
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _resolve_request_id(header_value: str | None) -> str:
    if header_value and _REQUEST_ID_PATTERN.fullmatch(header_value):
        return header_value
    return uuid4().hex


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _resolve_request_id(request.headers.get("x-request-id"))
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": 500,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            raise
        else:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response
        finally:
            request_id_ctx.reset(token)
