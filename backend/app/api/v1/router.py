"""v1 路由汇总。

约定：每个业务模块一个 endpoints 文件，在这里统一 include。
不要再往 main.py 里直接挂业务路由。
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/ping", tags=["meta"], summary="连通性测试")
async def ping() -> dict[str, str]:
    return {"pong": "ok"}


# ---- 后续里程碑逐步接入（取消注释即可）----
# from app.api.v1.endpoints import auth, rooms, reservations, admin
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
# api_router.include_router(reservations.router, prefix="/reservations", tags=["reservations"])
# api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
