"""Redis 客户端。

职责：
- 单例懒加载，导入本模块不发起连接
- 提供 ping / close 供健康检查与生命周期使用

TODO(M0)：
- [ ] get_redis() 单例
- [ ] ping_redis()
- [ ] close_redis()

后续用途：座位图缓存、分布式锁、令牌桶限流、ZSET 延迟任务。
"""
