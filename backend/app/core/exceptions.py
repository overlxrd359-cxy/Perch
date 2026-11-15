"""统一异常与错误响应。

约定响应体（前端只按 code 分支，**不要匹配 message 文本**）：

    {"code": "not_found", "message": "预约不存在", "request_id": "..."}

- 业务代码只抛 AppError 子类，不手写 JSONResponse
- 兜底 handler 绝不返回堆栈，堆栈只进日志
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx

logger = logging.getLogger(__name__)


class AppError(Exception):
    """业务异常基类。"""

    status_code: int = 400
    code: str = "bad_request"
    default_message: str = "请求有误"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.default_message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class BadRequest(AppError):
    status_code = 400
    code = "bad_request"
    default_message = "请求参数有误"


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"
    default_message = "请先登录"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"
    default_message = "无权访问该资源"


class NotFound(AppError):
    status_code = 404
    code = "not_found"
    default_message = "资源不存在"


class Conflict(AppError):
    status_code = 409
    code = "conflict"
    default_message = "资源冲突，请重试"


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"
    default_message = "请求过于频繁，请稍后再试"


_STATUS_CODE_MAP: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
}


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "request_id": request_id_ctx.get(),
        },
    )


async def _app_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, AppError):
        return _error_response(exc.status_code, exc.code, exc.message)
    # 理论上不会走到，防注册错了类型
    return _error_response(500, "internal_error", "服务器内部错误")


async def _validation_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    parts: list[str] = []
    for item in errors[:3]:
        location = ".".join(str(part) for part in item.get("loc", ()) if part != "body")
        message = str(item.get("msg", "参数不合法"))
        parts.append(f"{location} {message}".strip())
    detail = "；".join(parts) or "请求参数校验失败"
    return _error_response(422, "validation_error", f"参数校验失败：{detail}")


async def _http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):  # pragma: no cover - 防御性分支
        return _error_response(500, "internal_error", "服务器内部错误")

    code = _STATUS_CODE_MAP.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) and exc.detail else "请求失败"
    if exc.status_code == 404 and message == "Not Found":
        message = "接口不存在"
    return _error_response(exc.status_code, code, message)


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled exception",
        extra={"method": request.method, "path": request.url.path, "status": 500},
    )
    return _error_response(500, "internal_error", "服务器内部错误")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
