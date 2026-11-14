"""统一异常与错误响应。

约定：所有业务异常继承 AppError，响应体固定为
    {"code": "...", "message": "...", "request_id": "..."}
前端按 code 做分支，不要匹配 message 文本。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import request_id_ctx

logger = logging.getLogger(__name__)


class AppError(Exception):
    """业务异常基类。子类只需覆盖 code / status_code / default_message。"""

    code: str = "internal_error"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message: str = "服务器内部错误"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class BadRequestError(AppError):
    code = "bad_request"
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "请求参数有误"


class UnauthorizedError(AppError):
    code = "unauthorized"
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = "未登录或登录已过期"


class ForbiddenError(AppError):
    code = "forbidden"
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "没有权限执行该操作"


class NotFoundError(AppError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "资源不存在"


class ConflictError(AppError):
    """并发冲突 / 状态冲突，例如座位已被预约。"""

    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    default_message = "操作冲突，请刷新后重试"


class RateLimitedError(AppError):
    code = "rate_limited"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_message = "操作太频繁，请稍后再试"


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id_ctx.get(),
    }
    if details:
        body["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.exception("unhandled app error", exc_info=exc)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # 只回传字段路径与错误类型，不回传原始输入，避免把密码之类的值回显
        fields = [
            {"loc": ".".join(str(p) for p in err["loc"]), "type": err["type"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body("validation_error", "请求参数校验失败", {"fields": fields}),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # 绝不把堆栈返回给客户端
        logger.exception("unexpected error", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("internal_error", "服务器内部错误"),
        )
