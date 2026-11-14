"""应用入口。

启动顺序：配置（fail-fast）→ 日志 → 中间件 → 路由。
业务代码不要在这里堆逻辑。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.redis import close_redis
from app.db.session import engine
from app.middleware.request_id import RequestIdMiddleware

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    setup_logging("DEBUG" if settings.debug else "INFO")
    logger.info(
        "application starting",
        extra={"env": settings.env, "version": settings.app_version},
    )
    yield
    await close_redis()
    await engine.dispose()
    logger.info("application stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="智能自习室预约系统 API",
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # 注意顺序：Starlette 后添加的中间件在更外层。
    # RequestIdMiddleware 必须最外层，才能给 CORS 的异常响应也带上 request_id。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)

    from app.api.v1.endpoints.health import router as health_router

    app.include_router(health_router)
    app.include_router(api_router, prefix=API_PREFIX)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs" if settings.debug else "disabled",
        }

    return app


app = create_app()
