"""结构化日志。

职责：
- 输出 JSON 行，字段：ts / level / logger / msg / request_id / 可选业务字段
- 用 ContextVar 传递 request_id，业务代码无需手动传参
- 第三方库降噪（sqlalchemy / uvicorn.access / httpx / redis）

TODO(M0)：
- [ ] JsonFormatter
- [ ] request_id_ctx / user_id_ctx
- [ ] setup_logging() 幂等初始化

注意：日志只记白名单字段，禁止打印请求体全量（防密码入日志）。
"""
