"""统一异常与错误响应。

约定响应体：
    {"code": "...", "message": "...", "request_id": "..."}

前端按 code 分支，不要匹配 message 文本。

TODO(M0)：
- [ ] AppError 基类
- [ ] 子类：BadRequest / Unauthorized / Forbidden / NotFound / Conflict / RateLimited
- [ ] handler：AppError、RequestValidationError、StarletteHTTPException、兜底 Exception
- [ ] 兜底 handler 绝不返回堆栈
"""
