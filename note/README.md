# 开发笔记 · Perch 智能自习室预约系统

这里放开发过程中真正搞懂的东西，不是 API 手册的搬运。

原则：

- **能讲人话**：先讲“这东西解决什么问题”，再讲怎么用
- **贴项目代码**：每个知识点都指回仓库里的真实文件，不写脱离项目的玩具例子
- **记坑**：踩过的坑比顺利的部分更值钱
- **每篇结尾有自测**：答不上来就说明没读懂，回去补

---

## M0 阶段做了什么

M0 只做一件事：**让项目能启动、能被探活、能迁移、能过 CI**，业务一行不写。

| 能力 | 实现位置 | 说明 |
| --- | --- | --- |
| 配置系统 | `backend/app/core/config.py` | 缺必填项拒绝启动；生产环境拦截危险配置 |
| 时间工具 | `backend/app/core/time.py` | 全项目唯一的 UTC / 本地时间转换入口 |
| 结构化日志 | `backend/app/core/logging.py` | 单行 JSON，带 request_id |
| 请求 ID | `backend/app/middleware/request_id.py` | 每个请求一个 ID，贯穿日志与响应头 |
| 统一异常 | `backend/app/core/exceptions.py` | 固定错误响应体，前端按 code 分支 |
| 应用入口 | `backend/app/main.py` | 工厂函数 + lifespan + 中间件顺序 |
| 健康检查 | `backend/app/api/v1/endpoints/health.py` | `/healthz` 看进程，`/readyz` 看依赖 |
| 数据层 | `backend/app/db/session.py`、`db/base.py` | 异步 engine / session / ORM 基类 |
| Redis | `backend/app/core/redis.py` | 懒加载单例，import 不连库 |
| 迁移 | `backend/alembic/env.py` | Alembic 接管模型元数据 |
| 前端骨架 | `frontend/src/` | 双端路由、三套布局、占位页 |
| 工程化 | `Makefile`、`.github/workflows/ci.yml`、`docker-compose.yml` | 一条命令起依赖；CI 跑 lint + 类型 + 测试 |

验收结果：`/healthz` 200、`/readyz` 依赖挂掉 503、缺密钥拒绝启动、前端可访问、`make lint` 与 `make test` 全绿（13 条测试）。

---

## 章节索引

| # | 主题 | 读完你应该能回答 |
| --- | --- | --- |
| [01](./01-python环境与工程化.md) | Python 环境与工程化 | venv / uv / pyproject / ruff / mypy / pytest / CI 各管什么 |
| [02](./02-配置系统与fail-fast.md) | 配置系统 | 环境变量优先级、pydantic-settings 怎么用、为什么要 fail-fast |
| [03](./03-FastAPI应用骨架.md) | FastAPI 应用骨架 | ASGI 是什么、create_app 为什么这么写、中间件顺序为什么反直觉 |
| [04](./04-结构化日志与请求ID.md) | 日志与请求 ID | 为什么用 JSON、ContextVar 怎么跨函数传 ID、日志注入怎么防 |
| [05](./05-健康检查设计.md) | 健康检查 | liveness 与 readiness 的区别、为什么超时要用 wait_for |
| [06](./06-数据库与Alembic迁移.md) | 数据库与迁移 | 异步 engine 为何懒连接、session 怎么管、Alembic 怎么接管模型 |
| [07](./07-Redis异步客户端.md) | Redis 客户端 | 为什么懒加载、aclose 干什么、后面会拿它做什么 |
| [08](./08-前端骨架.md) | 前端骨架 | Vite / React 19 / Router 7 / TanStack Query / Tailwind 4 各自职责 |

建议顺序：01 → 02 → 03 → 04 → 05 → 06 → 07 → 08。  
03 和 04 有依赖关系（请求 ID 中间件挂载在应用上），先读 03 更顺。

---

## 怎么用这份笔记

1. 先读章节，遇到代码就打开对应文件对照
2. 每章末尾自测，能用自己的话答出来才算过
3. 改代码前想一想：这个改动会不会破坏本章讲的约定

**约定**：代码块里标了文件路径的，都是仓库真实代码（可能省略了无关行）；没标的才是示意例子。

---

## M1 预告（先混个脸熟）

下一阶段会用到这些，笔记会在 M1 完成后补：

- **Argon2id**：密码哈希，比 bcrypt 更抗 GPU 爆破
- **JWT**：access token 短时效 + refresh token 轮转
- **httpOnly Cookie**：JS 读不到的 Cookie，防 XSS 偷令牌
- **RBAC**：角色 → 权限点 → 接口，不写 `if role == "admin"`
- **限流**：Redis + Lua 做滑动窗口 / 令牌桶
- **审计日志**：谁在什么时候改了什么