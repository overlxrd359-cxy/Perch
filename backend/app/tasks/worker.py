"""后台 worker 入口。

职责：
- 启动日志、Redis 连通性检查
- 信号处理（SIGINT / SIGTERM）→ 优雅退出
- 周期循环，单次任务异常不能导致进程退出

TODO(M4)：
- [ ] ZSET 扫描：签到超时释放
- [ ] 违约结算与信用分扣减
- [ ] 预约提醒
- [ ] 多实例互斥（Redis 锁）

启动：python -m app.tasks.worker
"""
