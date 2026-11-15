"""v1 路由汇总。

约定：每个业务模块一个 endpoints 文件，在这里统一 include；
不要在 main.py 里直接挂业务路由。

M0 阶段这里只有空路由表，M1 起往里加：
- auth（注册 / 登录 / 刷新 / 登出）
- rooms（楼栋 / 自习室 / 座位图）
- reservations（预约 / 取消 / 改签 / 签到）
- admin（管理端）
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()
