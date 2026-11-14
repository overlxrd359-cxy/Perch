"""应用入口。

职责：
- 创建 FastAPI 实例（title / version / docs 开关按 env 区分）
- 按顺序注册中间件：CORS 在外，请求 ID 在最外层
- 注册异常处理器与路由
- 管理生命周期：启动日志、关闭 Redis 与数据库连接池

TODO(M0)：
- [ ] create_app() 工厂函数
- [ ] lifespan 上下文管理器
- [ ] 中间件注册顺序（顺序错了 request_id 会丢）
- [ ] include_router(api_router, prefix="/api/v1")
"""
