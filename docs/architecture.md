# 架构说明

## 形态

模块化单体（Modular Monolith）。单进程部署，模块边界清晰，未来要拆服务时按模块切，不按技术层切。

## 分层

```
api/            路由、依赖注入、请求/响应 schema
  ↓
services/       业务用例，事务边界在这一层
  ↓
models/         SQLAlchemy 模型
```

依赖单向向下。`core/` 是被所有层使用的横切能力（配置、日志、异常、Redis）。

**规则**：
- 路由函数里不写业务逻辑，只做参数解析和调用 service。
- service 不 import `api` 层。
- 跨模块调用走 service，不直接操作别人的 model。

## 目录职责

| 目录 | 职责 | 不该放什么 |
| --- | --- | --- |
| `app/api/` | HTTP 入口，路由与 schema | 业务规则、SQL |
| `app/services/` | 用例编排、事务、领域规则 | HTTP 相关的东西 |
| `app/models/` | 表结构定义 | 业务查询逻辑 |
| `app/schemas/` | Pydantic 模型 | ORM 模型 |
| `app/core/` | 配置、日志、异常、Redis、时间 | 业务代码 |
| `app/middleware/` | 请求级横切（请求 ID、审计、限流） | 领域逻辑 |
| `app/tasks/` | 后台定时任务 | 同步请求路径的代码 |
| `app/ai/` | RAG、Agent、Prompt、评测 | 通用业务代码 |
| `app/db/` | 引擎、会话、基类、模型注册 | 业务查询 |

## 请求生命周期

```
请求
 → RequestIdMiddleware     分配 request_id，写入 ContextVar
 → CORSMiddleware          跨域校验
 → 路由依赖（鉴权、限流）    未通过抛 AppError
 → service                业务逻辑 + 事务
 → JSONResponse            统一错误结构
 → 访问日志（JSON，带 request_id）
```

## 数据一致性策略

- 单库事务覆盖同一请求内的写操作。
- 跨模块副作用（通知、审计）用 outbox 表 + 后台投递，避免长事务。
- 定时任务多实例部署时用 Redis 锁保证互斥。

## 时间处理

- 数据库统一存 UTC 的 `DATETIME`（不带时区）。
- 全部转换集中在 `app/core/time.py`（M1 建立）。
- 业务代码禁止直接 `datetime.now()`。

## 鉴权

两层，缺一不可：

1. **接口级**：`require("permission:code")` 依赖，判断当前用户是否有权限点。
2. **对象级**：查询后校验资源归属，防止 IDOR（改 URL 里的 ID 读别人数据）。

## 前端

Vite + React SPA，单工程双布局：

- `AuthLayout`：登录/注册
- `UserLayout`：移动优先，学生端
- `AdminLayout`：桌面优先，管理端

状态分三类：
- 服务端状态 → TanStack Query
- 全局客户端状态（登录用户）→ Zustand
- 表单状态 → 组件内 useState

access token 只存内存；refresh token 由后端通过 httpOnly Cookie 下发，前端不可见。