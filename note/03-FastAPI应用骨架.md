# 03 · FastAPI 应用骨架

> 对应文件：`backend/app/main.py`、`backend/app/core/exceptions.py`、`backend/app/api/v1/`
> 目标：理解一个请求从 uvicorn 到路由函数之间到底经过了什么。

---

## 1. 先理解 ASGI

FastAPI 本身不监听端口，真正干活的是 **uvicorn**（ASGI 服务器）。

```
浏览器 → uvicorn（TCP/HTTP 解析）→ ASGI 应用（FastAPI）→ 你的路由函数
```

ASGI 应用本质上是一个可调用对象，签名固定：

```python
async def app(scope, receive, send):
    # scope:   请求元信息（method、path、headers、query）
    # receive: 用来读请求体
    # send:    用来发响应
```

好处：**协议与框架解耦**。同一个 FastAPI 应用既能跑在 uvicorn，也能被测试工具直接调用，不用真的开端口。

测试里就是这么干的：

```python
transport = httpx.ASGITransport(app=app)
async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
    response = await client.get("/healthz")
```

没有网络、没有端口、没有 sleep 等启动，**测试快且稳定**。

---

## 2. create_app 工厂模式

```python
def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(level="DEBUG" if settings.debug else "INFO")

    app = FastAPI(
        title="智能自习室预约系统",
        version=settings.app_version,
        docs_url=None if settings.is_prod else "/docs",
        openapi_url=None if settings.is_prod else "/openapi.json",
        lifespan=lifespan,
    )
    ...
    return app


app = create_app()
```

### 为什么用函数而不是直接在模块顶层堆

1. **可测试**：每个测试能 `create_app()` 造一个干净实例，互不污染
2. **可配置**：未来要给 worker / 不同入口造不同 app，改参数即可
3. **顺序可控**：配置 → 日志 → 应用 → 中间件，依赖关系一目了然

最后一行 `app = create_app()` 是为了兼容 `uvicorn app.main:app` 这种“模块:变量”的启动方式。

### 生产环境关文档

```python
docs_url=None if settings.is_prod else "/docs"
openapi_url=None if settings.is_prod else "/openapi.json"
```

`/docs` 会暴露全部接口结构，生产环境没必要给攻击者做地图。dev 保留方便调试。

---

## 3. lifespan：启动与关闭

```python
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("application started env=%s version=%s", settings.app_env, settings.app_version)
    yield
    await close_redis()
    await engine.dispose()
    logger.info("application stopped")
```

`yield` 之前是启动逻辑，之后是关闭逻辑。它替代了旧版 `@app.on_event("startup")`（已废弃）。

### 关键决定：启动时**不**连数据库

```python
# 这里只创建 engine 对象，没有 connect()
engine = create_async_engine(...)
```

如果启动时强制 `ping` MySQL，会出现：

- MySQL 还没初始化完 → 应用起不来 → 容器反复重启
- 数据库临时抖动 → 整个应用被重启，而其实只需要 `/readyz` 报 503

**“进程能启动”和“依赖可用”是两件事**，分别由 `/healthz` 和 `/readyz` 表达（见第 05 篇）。

关闭时释放资源则必须有：

```python
await close_redis()      # 关 Redis 连接池
await engine.dispose()   # 关数据库连接池
```

不关的话，热重载 / 测试多次建 app 会攒下一堆连接，把 MySQL 的 `max_connections` 耗光。

---

## 4. 中间件顺序（最容易搞反的地方）

```python
app.add_middleware(CORSMiddleware, ...)   # 先加
app.add_middleware(RequestIdMiddleware)   # 后加
```

直觉会以为“先加的在外层”，**实际上 Starlette 是反的**：后加的在外层。

### 为什么

Starlette 内部维护一个列表，`add_middleware` 每次都 **insert 到第 0 位**：

```
add CORS      → [CORS]
add RequestId → [RequestId, CORS]
```

构建时再 `reversed()` 逐个包：

```
reversed: [CORS, RequestId]
app = CORS(app)
app = RequestId(app)
```

于是最终结构是：

```
请求
 → ServerErrorMiddleware      （最外层，兜底 500）
   → RequestIdMiddleware      （后加 → 在外层）
     → CORSMiddleware         （先加 → 在内层）
       → ExceptionMiddleware  （异常 → handler）
         → 路由函数
```

所以 `RequestId` 能覆盖 CORS 的拒绝响应，也能给 404/422 加上 `X-Request-ID`。

**验证方法**：发一个 404，看响应头有没有 `x-request-id`；有，说明 RequestId 确实在最外层。

### CORS 的两个细节

```python
allow_origins=settings.cors_origin_list,
allow_credentials=True,
expose_headers=["X-Request-ID"],
```

- `allow_credentials=True` 时，`allow_origins` **不能用 `"*"`**。浏览器规范禁止通配符 + 凭据，FastAPI 会直接报错。所以必须维护白名单
- `expose_headers`：跨域时，浏览器默认只让 JS 读少数几个响应头。不写这行，前端读不到 `X-Request-ID`

---

## 5. 统一异常：让前端只认 code

### 5.1 异常类

```python
class AppError(Exception):
    status_code: int = 400
    code: str = "bad_request"
    default_message: str = "请求有误"

    def __init__(self, message=None, *, code=None, status_code=None):
        self.message = message or self.default_message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)
```

子类只声明差异：

```python
class NotFound(AppError):
    status_code = 404
    code = "not_found"
    default_message = "资源不存在"
```

业务代码这样用：

```python
raise NotFound("预约不存在")
raise Conflict("该座位该时段已被预约")
```

**不要**在路由里手写 `return JSONResponse(status_code=404, ...)`——那样错误格式会散落各处，前端没法统一处理。

### 5.2 四个 handler

| handler | 处理什么 | 输出 |
| --- | --- | --- |
| `_app_error_handler` | 业务异常 | 用异常自带的 status/code/message |
| `_validation_error_handler` | Pydantic 参数校验失败 | 422，把 `loc` + `msg` 拼成人话 |
| `_http_exception_handler` | Starlette 的 `HTTPException`（含 404 路由不存在） | 按状态码映射 code |
| `_unhandled_exception_handler` | 任何没接住的异常 | 500，**只记日志，不吐堆栈给用户** |

响应体统一：

```json
{"code": "not_found", "message": "接口不存在", "request_id": "6f8d7abc..."}
```

### 5.3 为什么 422 要转换

FastAPI 默认的校验错误长这样：

```json
{"detail": [{"loc": ["body", "password"], "msg": "Field required", "type": "missing"}]}
```

前端要写两套解析逻辑。转换后：

```json
{"code": "validation_error", "message": "参数校验失败：password Field required", "request_id": "..."}
```

前端只认 `code`，文案由后端给，改文案不用改前端。

```python
for item in errors[:3]:
    location = ".".join(str(part) for part in item.get("loc", ()) if part != "body")
```

只取前 3 条、去掉 `body` 前缀——不然一个 10 字段的表单报错会糊满屏幕。

### 5.4 兜底 handler 的一个冷知识

```python
async def _unhandled_exception_handler(request, exc):
    logger.exception("unhandled exception", ...)
    return _error_response(500, "internal_error", "服务器内部错误")
```

`Exception` 这个 handler 由 Starlette 最外层的 `ServerErrorMiddleware` 调用。它会把 500 响应发出去，**然后把异常重新抛出**，让服务器日志记录完整堆栈。

所以在测试里如果真触发了未捕获异常，`httpx.ASGITransport(raise_app_exceptions=True)`（默认）会直接把异常抛给测试，而不是返回 500。这是预期行为，不是 bug。

---

## 6. 路由组织

```python
app.include_router(health_router)                              # 根路径：/healthz /readyz
app.include_router(api_router, prefix=settings.api_v1_prefix)  # 业务：/api/v1/...
```

两条约定：

1. **健康检查放根路径**。部署侧的 healthcheck、Caddy、监控都按 `/healthz` 探活，挂到 `/api/v1` 下反而要处处改配置
2. **业务路由统一在 `api/v1/router.py` 汇总**，`main.py` 里不直接挂业务。以后加模块只改一个文件

```python
# app/api/v1/router.py
api_router = APIRouter()
# M1 起：
# api_router.include_router(auth.router, prefix="/auth")
```

---

## 自测

1. uvicorn 和 FastAPI 分别负责什么？ASGI 应用的可调用签名是什么？
2. 为什么用 `create_app()` 工厂，而不是在模块顶层直接创建？
3. `add_middleware` 先加的是内层还是外层？为什么？
4. 为什么 `allow_credentials=True` 时不能用 `allow_origins=["*"]`？
5. 业务代码为什么不该手写 `JSONResponse(status_code=404)`？
6. FastAPI 默认 422 响应长什么样？为什么要转换？
7. 未捕获异常时，为什么测试里可能看到异常直接抛出，而不是 500？