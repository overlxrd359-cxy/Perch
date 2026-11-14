# Campus Seat · 智能自习室预约系统

面向高校自习室的预约与管理系统。学生查空座、约座、签到；管理员管空间、审核、看数据；AI 助手能用自然语言查规则、查空位、辅助下单。

**当前进度：M0 工程地基完成**（骨架可运行，业务功能从 M1 开始接入）。

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

| 模块 | 功能 | 状态 |
| --- | --- | --- |
| 账号 | 注册、登录、找回密码、改密 | M1 |
| 找座 | 楼栋 → 自习室 → 座位图，按时段看空位，按插座/靠窗筛选 | M2–M3 |
| 预约 | 选时段、预约、改签、取消、重复检测 | M3 |
| 到店 | 签到码、签到时间窗、签退、超时自动释放 | M4 |
| 信用 | 信用分、违约记录、禁约期、申诉 | M4 |
| AI | 规则问答（带引用）、查空座、自然语言预约 | M7–M8 |

### 管理端（管理员，桌面优先）

| 模块 | 功能 | 状态 |
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
| ORM | **SQLAlchemy 2.0 async + asyncmy** | 2.0 类型化写法，asyncmy 是 MySQL 最快的 async 驱动 |
| 迁移 | **Alembic** | 禁止手改库，环境间保持一致 |
| 数据库 | **MySQL 8.0** | InnoDB 事务与唯一索引是防超卖的地基 |
| 缓存 / 锁 / 队列 | **Redis 7** | 座位图缓存、分布式锁、令牌桶、ZSET 延迟任务 |
| 向量库 | **Qdrant** | MySQL 无向量索引；单机轻量，占用约 300MB |
| AI 编排 | **LangGraph** | 状态图 + 中断恢复，适合带人工确认的 Agent |
| LLM | DeepSeek / 通义（OpenAI 兼容 API） | 轻量服务器跑不了本地大模型 |
| 前端 | **React 19 + TypeScript + Vite** | — |
| 样式 | **Tailwind CSS** | 原子类，不写 CSS 文件 |
| 组件 | **shadcn/ui** | 无样式组件 + Tailwind，代码进项目可改 |
| 数据请求 | **TanStack Query** | 缓存、重试、失效策略 |
| 状态 | **Zustand** | 只存登录态，不上 Redux |
| 部署 | **Docker Compose + Caddy** | 单机足够，Caddy 自动 HTTPS |
| CI | **GitHub Actions** | lint + 类型 + 测试 + 构建 |

**刻意不引入**：Kubernetes、Kafka、Elasticsearch、微服务拆分、Celery。
理由：单机规模下这些是负资产。什么时候该换，写在 `docs/architecture.md` 与技术方案里。

---

## 架构

```
                        ┌──────────────┐
   浏览器 ──HTTPS──▶    │    Caddy     │  自动证书 / 静态托管 / 反代
                        └──────┬───────┘
                               │ /api/*
                        ┌──────▼───────┐
                        │   FastAPI    │  异步、请求 ID、统一异常
                        │  (api层)     │
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
├── backend/                    后端服务
│   ├── app/
│   │   ├── main.py             应用入口：中间件、路由、生命周期
│   │   ├── core/               配置、日志、异常、Redis
│   │   │   ├── config.py       配置 + fail-fast 校验
│   │   │   ├── logging.py      JSON 结构化日志
│   │   │   ├── exceptions.py   统一错误码
│   │   │   └── redis.py        Redis 客户端
│   │   ├── db/                 引擎、会话、ORM 基类、模型注册
│   │   ├── middleware/         请求 ID、审计、限流（按里程碑扩展）
│   │   ├── api/v1/             路由层
│   │   │   ├── router.py       路由汇总
│   │   │   └── endpoints/      各模块端点（health 已实现）
│   │   ├── services/           业务用例（事务边界）
│   │   ├── models/             SQLAlchemy 模型
│   │   ├── schemas/            Pydantic 请求/响应
│   │   ├── tasks/              后台定时任务
│   │   └── ai/                 RAG / Agent / Prompt / 评测
│   ├── alembic/                数据库迁移
│   ├── tests/                  单元与集成测试
│   ├── Dockerfile              生产镜像（非 root）
│   └── pyproject.toml          依赖与工具配置
│
├── frontend/                   前端应用
│   └── src/
│       ├── main.tsx            入口
│       ├── router.tsx          路由表（双端）
│       ├── layouts/            AuthLayout / UserLayout / AdminLayout
│       ├── pages/              auth / user / admin
│       ├── components/         RequireAuth 守卫、UI 组件
│       ├── lib/                api 封装、登录态、QueryClient
│       └── styles/             Tailwind 入口
│
├── deploy/                     生产部署
│   ├── Caddyfile               反代 + HTTPS + 安全响应头
│   ├── docker-compose.prod.yml 生产编排
│   └── scripts/backup.sh       数据库备份
│
├── docs/                       架构与设计文档
├── docker-compose.yml          开发依赖（MySQL / Redis / Qdrant）
├── Makefile                    常用命令
├── .env.example                环境变量模板
├── 项目方案-...-v2完整版.md      技术方案
└── 项目计划书-....md            15 周执行计划
```

---

## 快速开始

### 前置要求

| 工具 | 版本 | 检查命令 |
| --- | --- | --- |
| Python | 3.12+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| Docker | 24+ | `docker --version` |
| uv（推荐） | 最新 | `uv --version` |

没装 uv 的话：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 1. 配置环境变量

```bash
cp .env.example .env
# 开发环境可直接用示例值；生产必须替换 SECRET_KEY 和所有密码
```

### 2. 启动依赖服务

```bash
make up
# 等价于：docker compose up -d
# 起来后：MySQL 3306 / Redis 6379 / Qdrant 6333，均只绑定 127.0.0.1
```

确认状态：

```bash
docker compose ps
```

### 3. 启动后端

```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

不想装 uv 的话：

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

验证：

```bash
curl http://127.0.0.1:8000/healthz    # {"status":"ok",...}
curl http://127.0.0.1:8000/readyz     # 检查 MySQL 与 Redis
```

接口文档：<http://127.0.0.1:8000/docs>（仅在 `DEBUG=true` 时开放）

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开 <http://localhost:5173>，会跳转到登录页。

> 如果 `npm run dev` 报 `vite: command not found`，说明 devDependencies 被跳过了：
> 环境里设了 `NODE_ENV=production`。改用 `npm install --include=dev` 重装即可。

> **注意**：登录/注册接口要到 M1 才实现，现在点登录会提示接口不存在。
> 这是预期行为，不是环境坏了。

---

## 常用命令

```bash
make up            # 启动 MySQL / Redis / Qdrant
make down          # 停止容器（保留数据）
make reset         # 停止并删除数据卷（会清空数据）
make backend       # 启动后端热重载
make frontend      # 启动前端
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
| `SECRET_KEY` | ✅ | JWT 签名密钥，至少 32 位。生成：`openssl rand -hex 32` |
| `ENV` | | `dev` / `test` / `prod`，默认 `dev` |
| `DEBUG` | | 生产必须为 `false`，否则拒绝启动 |
| `DATABASE_URL` | | MySQL 连接串，需带 `?charset=utf8mb4` |
| `REDIS_URL` | | Redis 连接串 |
| `QDRANT_URL` | | Qdrant 地址 |
| `CORS_ORIGINS` | | 逗号分隔的前端来源 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | access token 有效期，默认 15 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | | refresh token 有效期，默认 7 |

配置加载规则：环境变量 > 项目根 `.env` 文件。
缺必填项会**直接拒绝启动**并提示缺哪个，而不是跑到一半才报错。

---

## 开发路线

| 里程碑 | 内容 | 周次 |
| --- | --- | --- |
| **M0** | 工程地基（当前） | W1 |
| M1 | 认证、RBAC、安全基线 | W2–W3 |
| M2 | 空间管理（楼栋/自习室/座位） | W4 |
| M3 | 预约核心与防超卖 | W5–W6 |
| M4 | 签到、违约、定时任务 | W7 |
| M5 | 管理端完整 | W8–W9 |
| M7 | RAG 规则问答 | W10 |
| M8 | LangGraph 预约助手 | W11–W12 |
| M9 | 加固与压测 | W14 |
| M10 | 部署上线 | W15 |

详细任务、每周验收标准见 **`项目计划书-智能自习室预约系统.md`**。

---

## 文档

| 文档 | 内容 |
| --- | --- |
| `docs/architecture.md` | 分层、目录职责、请求生命周期、一致性策略 |
| `项目方案-智能自习室预约系统-v2完整版.md` | 产品定义、表结构、安全设计、并发方案、AI 设计 |
| `项目计划书-智能自习室预约系统.md` | 15 周排期、每周交付与验收、风险登记册 |

---

## 安全设计要点

完整威胁模型见技术方案第 5 章，这里只列骨架已落地的部分：

- **配置 fail-fast**：缺 `SECRET_KEY` 拒绝启动；生产环境检测到示例密钥也拒绝启动
- **统一错误结构**：`{code, message, request_id}`，不向前端泄露堆栈
- **请求 ID 贯穿**：每个请求分配 ID，日志与响应头都带，便于端到端排查
- **日志脱敏白名单**：只记录白名单字段，不打印请求体全量
- **CORS 白名单**：只允许配置的前端来源
- **依赖服务不暴露公网**：MySQL / Redis / Qdrant 均绑定 `127.0.0.1`
- **非 root 容器**：生产镜像以 uid 10001 运行

M1 起接入：Argon2id 密码哈希、refresh token 轮转与复用检测、RBAC + 对象级鉴权、CSP/HSTS。

---

## 开发约定

**后端**

- 路由函数只做参数解析和调用 service，不写业务逻辑
- 所有数据库变更必须走 Alembic 迁移，禁止手改库
- 新增模型必须在 `app/db/init_models.py` 里 import，否则 autogenerate 看不到
- 时间统一存 UTC，禁止在业务代码里裸调用 `datetime.now()`
- 提交前跑 `make lint && make test`

**前端**

- access token 只存内存，不写 localStorage
- 错误按 `code` 分支，不匹配 `message` 文本
- 列表页复用统一表格与分页组件，不每页重写

**提交信息**

```
feat(auth): 实现 refresh token 轮转
fix(reservation): 修复取消后缓存未失效
docs: 补充部署说明
```

---

## License

个人学习项目，未指定开源协议。如需引用请先联系作者。