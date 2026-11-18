"""v1 路由汇总。

约定：每个业务模块一个 endpoints 文件，在这里统一 include；
不要在 main.py 里直接挂业务路由。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth

api_router = APIRouter()
api_router.include_router(auth.router)

# M2 起：
# api_router.include_router(rooms.router, prefix="/rooms")
# api_router.include_router(reservations.router, prefix="/reservations")
