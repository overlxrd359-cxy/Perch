"""应用入口。

启动顺序很重要：
1. get_settings() 先跑 —— 配置非法就在这里失败（fail-fast），别等到第一个请求
2. setup_logging() 再跑 —— 之后所有日志都是 JSON
3. 中间件注册：CORS 先加，RequestId 最后加（Starlette 后加的在外层）
4. lifespan 只做资源释放；启动阶段**不**强制连接 MySQL/Redis
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.redis import close_redis
from app.db.session import engine
from app.middleware.request_id import RequestIdMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("application started env=%s version=%s", settings.app_env, settings.app_version)
    yield
    await close_redis()
    await engine.dispose()
    logger.info("application stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(level="DEBUG" if settings.debug else "INFO")

    app = FastAPI(
        title="智能自习室预约系统",
        version=settings.app_version,
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None if settings.is_prod else "/redoc",
        openapi_url=None if settings.is_prod else "/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    # 必须最后 add：后加的在外层，才能包住 CORS 产生的错误响应
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)

    # 健康检查挂根路径，业务路由挂 /api/v1；运维与 Caddy 都按根路径探活
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
