"""请求 ID 与访问日志中间件。

职责：
- 复用上游 X-Request-ID，没有则生成
- 写入 ContextVar，响应头回传
- 记录访问日志（method / path / status / duration_ms）

TODO(M0)：
- [ ] BaseHTTPMiddleware 实现
- [ ] 异常路径也要 reset ContextVar
- [ ] 响应头设置 X-Request-ID

注意：本中间件必须最后 add_middleware，才能包住 CORS 的异常响应。
"""
