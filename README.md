# Perch · 智能自习室预约系统

> **状态：骨架阶段（M0 进行中）**
> 目录、配置、部署脚本、文档已就位；业务实现尚未开始。
> **当前服务不可运行**，这是预期状态，不是环境坏了。

面向高校自习室的预约与管理系统。学生查空座、约座、签到；管理员管空间、审核、看数据；AI 助手能用自然语言查规则、查空位、辅助下单。

---

## 进度

> 详细任务清单与验收标准见 **[PLAN.md](./PLAN.md)**。开工前先读 PLAN，做完一项回去勾一项。

**当前：M0 工程地基 · 🚧 进行中**

```
阶段完成度  0 / 12
M0  工程地基          ██░░░░░░░░  🚧  1/12 任务     ← 当前位置
M1  认证与安全基线    ░░░░░░░░░░  ⬜  0/15 任务
M2  空间管理          ░░░░░░░░░░  ⬜  0/6  任务
M3  预约核心与防超卖  ░░░░░░░░░░  ⬜  0/9  任务
M4  到店与信用        ░░░░░░░░░░  ⬜  0/6  任务
M5  管理端完整        ░░░░░░░░░░  ⬜  0/8  任务
M6  前端双端（并行）  ░░░░░░░░░░  ⬜  随各阶段推进
M7  RAG 规则问答      ░░░░░░░░░░  ⬜  0/7  任务
M8  Agent 预约助手    ░░░░░░░░░░  ⬜  0/7  任务
M9  加固与压测        ░░░░░░░░░░  ⬜  0/6  任务
M10 部署上线          ░░░░░░░░░░  ⬜  0/6  任务
M11 加分项            ░░░░░░░░░░  ⬜  弹性
```

---

## 为什么做这个

自习室座位靠"人肉占座 + 群里喊"，导致三个问题：

- **看不见**：哪有空位全靠跑，白跑一趟是常事
- **说不清**：占了座不来，没人管，也没有违约记录
- **管不了**：管理员没有数据，不知道哪个时段最挤、谁总爽约

这个项目把它变成可预约、可追溯、可运营的系统。

---

## 功能规划

### 用户端（学生，移动优先）

| 模块 | 功能 | 计划阶段 |
| --- | --- | --- |
| 账号 | 注册、登录、找回密码、改密 | M1 |
| 找座 | 楼栋 → 自习室 → 座位图，按时段看空位，按插座/靠窗筛选 | M2–M3 |
| 预约 | 选时段、预约、改签、取消、重复检测 | M3 |
| 到店 | 签到码、签到时间窗、签退、超时自动释放 | M4 |
| 信用 | 信用分、违约记录、禁约期、申诉 | M4 |
| AI | 规则问答（带引用）、查空座、自然语言预约 | M7–M8 |

### 管理端（管理员，桌面优先）

| 模块 | 功能 | 计划阶段 |
| --- | --- | --- |
| 仪表盘 | 今日预约、在座数、上座率、违约率、趋势 | M5 |
| 空间 | 自习室 CRUD、座位批量生成、启停、闭馆日 | M2 |
| 预约 | 多条件查询、强制取消、代客改签、导出 | M5 |
| 用户 | 列表、禁用、重置密码、角色调整 | M5 |
| 配置 | 预约规则参数化（时长、次数、签到窗口、扣分） | M5 |
| 审计 | 操作日志：谁在何时改了什么 | M1 起 |
| 知识库 | 规则文档维护、重建索引 | M7 |

---

## 技术栈

| 层 | 选型 | 选择理由 |
| --- | --- | --- |
| 后端框架 | **FastAPI**（全异步） | 原生 async、OpenAPI、依赖注入 |
| 语言 | Python 3.12+ | — |
| 包管理 | **uv** | 比 pip/poetry 快一个量级，锁文件可靠 |
| ORM | **SQLAlchemy 2.0 async + asyncmy** | 2.0 类型化写法；asyncmy 是 MySQL 最快的 async 驱动 |
| 迁移 | **Alembic** | 禁止手改库，环境间保持一致 |
| 数据库 | **MySQL 8.0** | InnoDB 事务与唯一索引是防超卖的地基 |
| 缓存 / 锁 / 队列 | **Redis 7** | 座位图缓存、分布式锁、令牌桶、ZSET 延迟任务 |
| 向量库 | **Qdrant** | MySQL 无向量索引；单机轻量，约占 300MB |
| AI 编排 | **LangGraph** | 状态图 + 中断恢复，适合带人工确认的 Agent |
| LLM | DeepSeek / 通义（OpenAI 兼容 API） | 轻量服务器跑不了本地大模型 |
| 前端 | **React 19 + TypeScript + Vite** | 登录后才有内容，SSR 无收益，省一个 Node 进程 |
| 样式 | **Tailwind CSS** | 原子类，不写 CSS 文件 |
| 组件 | **shadcn/ui** | 无样式组件 + Tailwind，代码进项目可改 |
| 数据请求 | **TanStack Query** | 缓存、重试、失效策略 |
| 状态 | **Zustand** | 只存登录态，不上 Redux |
| 部署 | **Docker Compose + Caddy** | 单机足够，Caddy 自动 HTTPS |
| CI | **GitHub Actions** | lint + 类型 + 测试 + 构建 |

**刻意不引入**：Kubernetes、Kafka、Elasticsearch、微服务拆分、Celery。
理由：单机规模下这些是负资产。什么时候该换，见 `docs/architecture.md`。

---

## 架构

```
                        ┌──────────────┐
   浏览器 ──HTTPS──▶    │    Caddy     │  自动证书 / 静态托管 / 反代
                        └──────┬───────┘
                               │ /api/*
                        ┌──────▼───────┐
                        │   FastAPI    │  异步、请求 ID、统一异常
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │  services    │  业务用例、事务边界
                        └──┬────┬───┬──┘
                           │    │   │
              ┌────────────▼┐ ┌─▼───┴────┐ ┌──────────┐
              │   MySQL 8   │ │  Redis 7 │ │  Qdrant  │
              │  业务数据    │ │ 缓存/锁  │ │  向量库  │
              └─────────────┘ └──────────┘ └──────────┘
                           ▲
                    ┌──────┴───────┐
                    │    worker    │  定时任务：超时释放、违约结算
                    └──────────────┘
```

分层原则：`api → services → models` 单向依赖。路由不写业务逻辑，service 不碰 HTTP。

---

## 目录结构

```
.
├── PLAN.md                     进度事实源：开工前必读
├── backend/
│   ├── app/
│   │   ├── main.py             应用入口
│   │   ├── core/               config / logging / exceptions / redis
│   │   ├── db/                 引擎、会话、ORM 基类、模型注册
│   │   ├── middleware/         请求 ID（后续：审计、限流）
│   │   ├── api/v1/             路由层
│   │   │   ├── router.py       路由汇总
│   │   │   └── endpoints/      各模块端点
│   │   ├── services/           业务用例（事务边界）
│   │   ├── models/             SQLAlchemy 模型
│   │   ├── schemas/            Pydantic 请求/响应
│   │   ├── tasks/              后台定时任务
│   │   └── ai/                 rag / agent / prompts / eval
│   ├── alembic/                数据库迁移
│   ├── tests/                  测试
│   ├── Dockerfile              生产镜像（非 root）
│   └── pyproject.toml          依赖与工具配置
│
├── frontend/
│   └── src/
│       ├── main.tsx            入口
│       ├── router.tsx          路由表（双端）
│       ├── layouts/            Auth / User / Admin 三套布局
│       ├── pages/              auth / user / admin
│       ├── components/         RequireAuth 守卫、UI 组件
│       ├── lib/                api 封装、登录态、QueryClient
│       └── styles/             Tailwind 入口
│
├── deploy/
│   ├── Caddyfile               反代 + HTTPS + 安全响应头
│   ├── docker-compose.prod.yml 生产编排
│   └── scripts/backup.sh       数据库备份
│
├── docs/architecture.md        分层与约定
├── docker-compose.yml          开发依赖（MySQL / Redis / Qdrant）
├── Makefile                    常用命令
├── .env.example                环境变量模板
├── 项目计划书-....md            任务拆解、工时、验收、风险
└── 项目方案-...-v2完整版.md     产品与安全设计
```

> `backend/app/` 与 `frontend/src/` 下的 `.py` / `.tsx` **目前全是占位文件**：
> 只有 docstring 说明职责和 TODO 清单，没有实现。按 PLAN 逐个填。

---

## 当前可用性

| 能力 | 现在 | 什么时候能用 |
| --- | --- | --- |
| 起 MySQL / Redis / Qdrant | ✅ `make up` 可用 | 已可 |
| 起后端服务 | ❌ 入口未实现 | M0-7 完成后 |
| 打开前端页面 | ❌ 入口未挂载 | M0-9 完成后 |
| 注册登录 | ❌ | M1 完成后 |
| 预约座位 | ❌ | M3 完成后 |

**现在能做的**：读结构、读 PLAN、跑 `make up` 起依赖、跑 lint 与测试（都是空的但链路通）。

---

## 环境准备

| 工具 | 版本 | 检查 |
| --- | --- | --- |
| Python | 3.12+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| Docker | 24+ | `docker --version` |
| uv（推荐） | 最新 | `uv --version` |

没装 uv：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

配置：

```bash
cp .env.example .env      # 开发可直接用示例值
```

装依赖：

```bash
cd backend && uv sync --extra dev
# 或不用 uv：
# python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

cd ../frontend && npm install --include=dev
```

> `--include=dev` 别漏：环境里若有 `NODE_ENV=production`，npm 会跳过 devDependencies，
> 导致 `vite` / `tsc` 缺失。

---

## 常用命令

```bash
make up            # 启动 MySQL / Redis / Qdrant
make down          # 停止容器（保留数据）
make reset         # 停止并删除数据卷（会清空数据）
make backend       # 启动后端（M0-7 后才可用）
make frontend      # 启动前端（M0-9 后才可用）
make test          # 跑后端测试
make lint          # ruff + mypy
make fmt           # 自动格式化
make migrate m="add users"   # 生成迁移
make upgrade       # 应用迁移
make health        # 查看后端健康状态
```

---

## 环境变量

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `SECRET_KEY` | ✅ | JWT 签名密钥，≥32 位。生成：`openssl rand -hex 32` |
| `APP_ENV` | | `dev` / `test` / `prod`，默认 `dev`（不要叫 `ENV`：它是 DSH 启动保留变量，会让 `dsh`/`dst` 在该目录下拒绝启动） |
| `DEBUG` | | 生产必须 `false` |
| `DATABASE_URL` | | MySQL 连接串，需带 `?charset=utf8mb4` |
| `REDIS_URL` | | Redis 连接串 |
| `QDRANT_URL` | | Qdrant 地址 |
| `CORS_ORIGINS` | | 逗号分隔的前端来源 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | access token 有效期，默认 15 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | | refresh token 有效期，默认 7 |

加载规则：环境变量 > 项目根 `.env`。缺必填项应**拒绝启动**并提示缺哪个（M0-1 实现）。

---

## 开发约定

**后端**

- 路由函数只做参数解析和调用 service，不写业务逻辑
- 所有数据库变更走 Alembic 迁移，禁止手改库
- 新增模型必须在 `app/db/init_models.py` 里 import，否则 autogenerate 看不到
- 时间统一存 UTC，业务代码禁止裸调 `datetime.now()`
- 提交前跑 `make lint && make test`

**前端**

- access token 只存内存，不写 localStorage
- 错误按 `code` 分支，不匹配 `message` 文本
- 列表页复用统一表格与分页组件

**提交信息**

```
feat(auth): 实现 refresh token 轮转
fix(reservation): 修复取消后缓存未失效
docs(plan): 勾选 M0-2
```

---

## 文档

| 文档 | 内容 |
| --- | --- |
| **[PLAN.md](./PLAN.md)** | 进度事实源，任务勾选与阶段状态 |
| `项目计划书-智能自习室预约系统.md` | 15 周排期、每周交付与验收、风险登记册 |
| `项目方案-智能自习室预约系统-v2完整版.md` | 产品定义、表结构、安全设计、并发方案、AI 设计 |
| `docs/architecture.md` | 分层、目录职责、请求生命周期、一致性策略 |

---

## License

个人学习项目，未指定开源协议。如需引用请先联系作者。