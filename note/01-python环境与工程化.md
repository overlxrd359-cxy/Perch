# 01 · Python 环境与工程化

> 目标：搞清楚一个 Python 项目从“能跑”到“能长期维护”需要哪些基础设施。
> 本篇对应仓库里的 `backend/pyproject.toml`、`Makefile`、`.github/workflows/ci.yml`、`docker-compose.yml`。

---

## 1. 虚拟环境：解决“依赖打架”

### 问题

系统里只有一个 Python，A 项目要 `pydantic 1.x`，B 项目要 `pydantic 2.x`，装在一起必炸。

### 虚拟环境做什么

它复制一份“独立的包安装目录”（`site-packages`），让每个项目只看到自己的依赖。

本项目里的位置：

```
backend/.venv/          # 虚拟环境
backend/.venv/bin/python    # 这个环境里的解释器
backend/.venv/bin/pytest    # 装在这个环境里的命令
```

手工创建：

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

`-e` 是 editable（可编辑安装）：代码改了不用重装，适合开发。

### uv 是什么

`uv` 是 Astral 用 Rust 写的 Python 包管理器，把 `venv + pip + pip-tools` 的活一起干了，速度快一个量级。

```bash
uv sync --extra dev     # 按 pyproject 建环境、装依赖（CI 用这个）
uv run pytest           # 在项目环境里执行命令，不用手动 activate
```

**本机没装 uv 也能开发**：仓库里的 `.venv` 已经建好，Makefile 直接调 `.venv/bin/*`，不依赖 uv，也不依赖你是否 activate 了环境。

> 这就是为什么 Makefile 里写 `.venv/bin/uvicorn` 而不是 `uvicorn`：
> 后者要求你先 `source .venv/bin/activate`，忘一次就用到全局环境，报错还很难懂。

---

## 2. pyproject.toml：项目唯一配置入口

`backend/pyproject.toml` 同时承担四件事：依赖声明、构建配置、lint 配置、测试配置。

### 2.1 依赖

```toml
[project]
name = "campus-seat"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncmy>=0.2.9",
    "cryptography>=43.0.0",  # MySQL caching_sha2_password 认证需要
    "alembic>=1.14.0",
    "redis>=5.2.0",
    "pyjwt>=2.10.0",
    "argon2-cffi>=23.1.0",
    "python-multipart>=0.0.12",
]
```

几个细节：

- `uvicorn[standard]`：方括号叫 **extra**，装上 uvloop、httptools 这些可选加速件
- `sqlalchemy[asyncio]`：装 SQLAlchemy 的异步支持（依赖 greenlet）
- `cryptography` 不是随便加的：MySQL 8 默认用 `caching_sha2_password` 认证，asyncmy 需要它做 RSA 交换，**不装就报 `cryptography package is required`**。这个坑我在 M0 真踩了
- 版本用 `>=` 下限而不是 `==` 锁定：锁版本交给 `uv.lock`，`pyproject` 只表达兼容范围

开发依赖单独放：

```toml
[project.optional-dependencies]
dev = ["ruff>=0.8.0", "mypy>=1.13.0", "pytest>=8.3.0", "pytest-asyncio>=0.24.0", "httpx>=0.28.0"]
```

生产镜像只装 `dependencies`，不装 `dev`，镜像能小几百 MB。

### 2.2 构建

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.uv]
package = true
```

意思是：这个项目本身可以被当成包安装（`pip install -e .`），包内容就是 `app/` 目录。
好处是 `from app.core.config import ...` 在任何工作目录都能 import，不靠“当前目录恰好在 sys.path 里”这种玄学。

---

## 3. Ruff：lint + format 一把梭

过去要装 `flake8 + isort + black` 三件套，Ruff 用 Rust 重写后一个工具全包，还快。

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
src = ["."]
```

`src` 这行有个真实的坑：一开始写的是 `["app", "tests"]`，结果 Ruff 把 `app` 当成了“第三方包”，导入顺序检查把 `from app...` 排到 `pydantic` 后面，还要求去掉分组空行。改成 `["."]` 后，`app` 才被正确识别为第一方代码。**配置错的时候，工具不会报“你配错了”，只会给你一堆莫名其妙的提示。**

规则选择：

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "ASYNC", "S", "RUF"]
```

| 前缀 | 管什么 | 举例子 |
| --- | --- | --- |
| `E` | pycodestyle 错误 | 行尾空格、缩进不对 |
| `F` | pyflakes | 未使用变量、未定义名字 |
| `I` | isort | import 排序 |
| `N` | pep8-naming | 类名要 CapWords，函数要 snake_case |
| `UP` | pyupgrade | 用新语法：`X | None` 替代 `Optional[X]` |
| `B` | bugbear | 函数默认值可变对象、循环里 return 之类 |
| `SIM` | simplify | 可以简化的写法 |
| `ASYNC` | async 专项 | async 函数里调阻塞代码 |
| `S` | bandit 安全 | `eval`、硬编码密码 |
| `RUF` | Ruff 自家规则 | 杂项 |

`ignore` 里的每条都有理由，不是“报了我就关”：

```toml
ignore = [
    "B008",   # FastAPI Depends 是函数调用默认值，属于框架约定
    "S104",   # 绑定 0.0.0.0 在容器内是必要行为
    "N818",   # BadRequest / NotFound 这类领域异常名，加 Error 后缀反而啰嗦
]
```

`per-file-ignores` 也很关键：测试里允许 `assert`（`S101`）、允许假密码（`S105/106`）、允许先设环境变量再 import（`E402`）。

```toml
[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101", "S105", "S106", "E402"]
"alembic/*" = ["E501"]
```

---

## 4. Mypy：在运行前发现类型错误

Python 是动态类型，`user.nmae` 拼错要到运行时才炸。mypy 靠类型注解做静态检查。

```toml
[tool.mypy]
python_version = "3.12"
plugins = ["pydantic.mypy"]
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
show_error_codes = true
```

- `disallow_untyped_defs`：函数必须写参数和返回类型，逼你把意图写清楚
- `plugins = ["pydantic.mypy"]`：让 mypy 理解 Pydantic 的 `Field`、`model_validator`，否则会误报
- `show_error_codes`：报错带 `[arg-type]` 这种码，方便查文档

写起来是这样：

```python
async def get_session() -> AsyncIterator[AsyncSession]:
    ...
```

返回类型写成 `AsyncIterator[AsyncSession]` 而不是 `AsyncSession`，因为带 `yield` 的函数返回的是生成器/异步迭代器。

---

## 5. Pytest：异步测试要显式配置

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
addopts = "-q"
```

- `asyncio_mode = "auto"`：`async def test_xxx()` 不用加 `@pytest.mark.asyncio`，pytest-asyncio 自动接管
- `asyncio_default_fixture_loop_scope = "function"`：每个测试一个事件循环，测试之间不共享 loop，避免“client 绑定在旧 loop 上”的怪问题
- `addopts = "-q"`：默认安静输出，失败时才展开

`tests/conftest.py` 里有个顺序问题必须理解：

```python
import os

# 必须先设环境变量，再 import app
os.environ["SECRET_KEY"] = "test-secret-key-..."
os.environ["APP_ENV"] = "test"

from app.main import create_app  # noqa: E402
```

因为 `app.core.config` 在 **import 时**就会读配置、做校验。顺序反了，CI 上（没有 `.env`）直接 `ValidationError`，一个测试都跑不起来。

用 `os.environ[...] = ...` 而不是 `setdefault`：你的 shell 里可能残留 `.env` 的 `APP_ENV=dev`，`setdefault` 挡不住，测试会悄悄跑在 dev 配置上。

---

## 6. Makefile：把命令固定下来

```make
backend: ## 启动后端开发服务器（热重载）
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

lint: ## 运行 ruff 与 mypy
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app

test: ## 运行后端测试
	cd backend && .venv/bin/pytest
```

为什么值得维护一个 Makefile：

1. 新人不用猜命令，`make` 一下列出全部
2. CI 和本地跑的是同一套命令，避免“我本地是好的”
3. 命令写错一次，改一处，不用满文档找

`make lint` 是三个检查串联：`ruff check`（规则）、`ruff format --check`（格式）、`mypy`（类型）。任何一步失败，整体失败。

---

## 7. CI：把门禁搬到 PR 上

```yaml
jobs:
  backend:
    steps:
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --extra dev
      - run: uv run ruff check .
      - run: uv run mypy app
      - run: uv run pytest

  frontend:
    steps:
      - run: npm ci --include=dev --no-audit --no-fund
      - run: npm run typecheck
      - run: npm run build
```

两个细节：

- **`npm ci` 而不是 `npm install`**：严格按 `package-lock.json` 装，保证 CI 与本地一致
- **`--include=dev` 别漏**：环境里若有 `NODE_ENV=production`，npm 会跳过 devDependencies，`vite`/`tsc` 直接消失

CI 的价值不是“跑给别人看”，而是**让“没跑测试就合进去”这件事变得不可能**。

---

## 8. Docker Compose：开发依赖一条命令起

`docker-compose.yml` 里三个服务：MySQL 8、Redis 7、Qdrant。

```yaml
mysql:
  ports:
    - "127.0.0.1:${MYSQL_PORT:-3306}:3306"
  healthcheck:
    test: ["CMD-SHELL", "mysqladmin ping -h 127.0.0.1 -uroot -p$$MYSQL_ROOT_PASSWORD --silent"]
```

逐条解释：

- `127.0.0.1:3306:3306`：宿主端口:容器端口。绑 `127.0.0.1` 表示只允许本机访问，不暴露到局域网/公网
- `${MYSQL_PORT:-3306}`：读环境变量，没有就用 3306
- `healthcheck`：容器“起来了”不等于“能用了”。MySQL 初始化要几十秒，healthcheck 通过才算真的就绪
- `volumes`：数据存命名卷，`docker compose down` 不会丢；`down -v` 才会删

### 踩过的坑：端口被系统 MySQL 占用

本机装了原生 MySQL 9.7，占着 3306，容器映射时直接报：

```
Error response from daemon: ports are not available: ... bind: address already in use
```

处理方式：本地 `.env` 把 `MYSQL_PORT` 和 `DATABASE_URL` 的端口改成 3307，**不修改项目的默认值**，别人的环境不受影响。

还有一个更隐蔽的坑：**shell 里的环境变量优先级高于 `.env`**。如果 shell 里残留了 `DATABASE_URL`，改 `.env` 是不生效的，排查时先：

```bash
env | grep -E 'DATABASE_URL|MYSQL_PORT'
```

---

## 自测

1. 为什么 Makefile 里用 `.venv/bin/uvicorn`，而不是 `uvicorn`？
2. `pyproject.toml` 里 `dependencies` 和 `optional-dependencies.dev` 的区别是什么？生产镜像该装哪个？
3. Ruff 的 `src` 配错会表现成什么问题？为什么不报“配置错误”？
4. `conftest.py` 为什么必须“先设环境变量再 import app”？用 `setdefault` 有什么隐患？
5. 容器 `Up` 和 `healthy` 的区别是什么？为什么 MySQL 要配 healthcheck？

答案都在正文里，答不上来就回去看对应小节。