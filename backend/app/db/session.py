"""数据库引擎与会话。

职责：
- create_async_engine（asyncmy 驱动）
- async_sessionmaker，expire_on_commit=False
- get_session() 作为 FastAPI 依赖，每请求一个 session

TODO(M0)：
- [ ] engine 与连接池参数（pool_size / max_overflow / pool_recycle）
- [ ] SessionLocal
- [ ] get_session() 依赖

注意：pool_pre_ping=True，避免 MySQL 空闲断连。
"""
