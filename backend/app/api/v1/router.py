"""v1 路由汇总。

约定：每个业务模块一个 endpoints 文件，在这里统一 include。
不要在 main.py 里直接挂业务路由。

TODO(M1)：
- [ ] include_router(auth.router, prefix="/auth")
- [ ] include_router(rooms.router, prefix="/rooms")
- [ ] include_router(reservations.router, prefix="/reservations")
- [ ] include_router(admin.router, prefix="/admin")
"""
