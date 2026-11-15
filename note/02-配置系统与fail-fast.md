# 02 · 配置系统与 fail-fast

> 对应文件：`backend/app/core/config.py`
> 目标：所有配置只有一个来源、非法配置在启动时就死、报错能看懂。

---

## 1. 配置该放在哪

常见几种做法，按成熟度排：

| 做法 | 问题 |
| --- | --- |
| 代码里写死 `SECRET_KEY = "..."` | 密钥进 git，等于公开 |
| 到处 `os.getenv("XXX")` | 拼写错不报错，返回 `None`，跑到业务层才炸 |
| 统一 `Settings` 类 + 启动时校验 | ✅ 本项目采用 |

第三个做法的核心思想叫 **12-Factor App 的 Config**：配置从环境读取，代码与配置分离。同一个镜像，通过环境变量决定连测试库还是生产库。

---

## 2. pydantic-settings 是什么

`pydantic` 负责“定义数据结构 + 校验”，`pydantic-settings` 在它上面加了一层 **从环境变量 / .env 文件自动填充** 的能力。

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "dev"
    secret_key: str
```

`Settings()` 一实例化，就会按顺序去找值：

```
1. 显式传参        Settings(secret_key="xxx")
2. 环境变量        SECRET_KEY=xxx
3. .env 文件       .env 里的 SECRET_KEY=xxx
4. 字段默认值      "dev"
```

**优先级从高到低**，先找到的赢。这就是为什么“我改了 `.env` 怎么没生效”——先查环境变量。

> 字段名 `secret_key` 对应环境变量 `SECRET_KEY`，默认大小写不敏感（`case_sensitive=False`）。

---

## 3. 逐段读项目里的 Settings

### 3.1 定位 .env

```python
# backend/app/core/config.py -> core -> app -> backend -> 项目根
ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"
```

`__file__` 是当前文件路径，`resolve()` 转绝对路径，`parents[3]` 往上数四层：

```
config.py 的父目录:        core          parents[0]
再上一层:                  app           parents[1]
再上一层:                  backend       parents[2]
再上一层:                  项目根         parents[3]
```

这样不管从哪个目录启动（`make backend`、`uvicorn`、pytest），都能找到项目根的 `.env`。
**用相对路径 `".env"` 就会随工作目录漂移**，是常见 bug。

### 3.2 元配置

```python
model_config = SettingsConfigDict(
    env_file=ENV_FILE,
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
)
```

- `env_file`：读哪个文件
- `env_file_encoding`：中文注释要用 utf-8
- `case_sensitive=False`：`APP_ENV` / `app_env` 都认
- `extra="ignore"`：`.env` 里多出来的键（比如 `MYSQL_ROOT_PASSWORD`、`VITE_API_BASE_URL`）不报错。
  如果设成 `forbid`，加一个 compose 用的变量就会让应用起不来——**配置类只关心自己用的字段**

### 3.3 字段与校验

```python
app_env: Literal["dev", "test", "prod"] = "dev"
secret_key: str = Field(min_length=32, description="JWT 签名密钥，至少 32 位")
access_token_expire_minutes: int = 15
```

- `Literal`：只允许这三个值，写 `APP_ENV=production` 会直接被拒（拼错环境名是最常见的配置事故）
- `Field(min_length=32)`：必填 + 长度约束。没有默认值 = 必填
- `int` 字段：环境变量都是字符串，pydantic 会自动转 `"15"` → `15`，转不了就报错

### 3.4 派生属性

```python
@property
def cors_origin_list(self) -> list[str]:
    return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
```

为什么不直接写 `cors_origins: list[str]`？

> **pydantic-settings 对 list 类型的字段按 JSON 解析**。你写 `CORS_ORIGINS=http://a,http://b`，
> 它会尝试 `json.loads`，直接报 `JSONDecodeError`。
> 必须写成 `["http://a","http://b"]` 这种 JSON 数组才行——但在 `.env` 里写 JSON 很难看也容易错。

所以这里用 `str` 存原始值，用 property 拆。**存储格式与使用格式分开**，是处理这类问题的通用套路。

### 3.5 字段级校验：清洗

```python
@field_validator("secret_key")
@classmethod
def _strip_secret(cls, value: str) -> str:
    return value.strip()
```

`field_validator` 在单个字段赋值时跑。这里防的是 `.env` 里复制粘贴带的空格/换行——一个尾部空格会让签名密钥完全变样，排查起来极其痛苦。

### 3.6 模型级校验：生产环境红线

```python
@model_validator(mode="after")
def _check_production_safety(self) -> Settings:
    if not self.is_prod:
        return self
    if self.debug:
        raise ValueError("生产环境必须 DEBUG=false")
    lowered = self.secret_key.lower()
    if any(marker in lowered for marker in _DEV_SECRET_MARKERS):
        raise ValueError("生产环境检测到示例 SECRET_KEY，请用 `openssl rand -hex 32` 重新生成")
    return self
```

`mode="after"` 表示所有字段都校验完之后再跑，这时能同时看到多个字段（比如 `app_env` 和 `debug`）。

拦的两条都是真实事故：

1. **生产开 DEBUG**：报错页会把源码、变量、SQL 全吐给用户
2. **示例密钥没换**：`dev-only-secret-key-change-me...` 一旦上生产，任何人都能伪造 JWT

判断方式很土但有效：密钥里含 `dev-only` / `change-me` / `changeme` 就算没换。

---

## 4. fail-fast：为什么要在启动时死

```python
@lru_cache
def _load_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    try:
        return _load_settings()
    except ValidationError as exc:
        raise SystemExit(_format_config_error(exc)) from None
```

### 4.1 不带病启动

如果配置错了还让进程起来，会发生什么：

- 第一个请求进来才炸 → 用户看到 500，日志里一堆 traceback
- 或者更糟：配置错了但“看起来能跑”，跑了一小时才发现连的是测试库

**启动时死是好事**。容器编排会看到进程退出 → 重启 → 一直失败 → 报警。问题在 30 秒内暴露，而不是在业务高峰。

### 4.2 为什么 `SystemExit` 而不是普通异常

```python
raise SystemExit("配置校验失败……") from None
```

- `SystemExit` 让 Python 直接退出，不打印 traceback，只打印消息
- `from None` 抑制“During handling of the above exception...”这种链式噪音
- 对比一下：`raise RuntimeError` 会带一整屏调用栈，运维根本不想看

实际输出（删掉 `SECRET_KEY` 时）：

```
配置校验失败，进程拒绝启动。
请检查项目根目录的 .env（字段清单见 .env.example）：
  - secret_key: Field required
提示：SECRET_KEY 用 `openssl rand -hex 32` 生成；生产环境还需要 APP_ENV=prod、DEBUG=false。
```

### 4.3 缓存：一个进程只读一次

```python
@lru_cache
def _load_settings() -> Settings:
    return Settings()
```

配置在进程生命周期内不变，没必要每个请求都重新解析 `.env`（还有 I/O）。

`get_settings()` 是全局入口，业务代码这样用：

```python
from app.core.config import get_settings

settings = get_settings()
```

`lru_cache` 有个副作用：**测试里改了环境变量不会生效**。所以测试配置时直接 `Settings(_env_file=None, ...)` 造新实例，而不是依赖全局单例。

---

## 5. 测试怎么写

```python
# backend/tests/test_config.py
def test_missing_secret_key_is_rejected(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "secret_key" in str(exc_info.value)
```

关键在 `_env_file=None`：**不读 .env**，只按当前环境变量构造。否则本地 `.env` 里有密钥，这个测试永远失败。

`monkeypatch` 是 pytest 的 fixture，测试结束自动还原环境变量，不用手写 `try/finally`。

---

## 6. 踩坑记录

**坑 1：改了 `.env` 不生效**
shell 里已有同名环境变量，优先级更高：

```bash
env | grep DATABASE_URL
# DATABASE_URL=mysql+asyncmy://...:3306/...   ← 它在覆盖你的 .env
```

**坑 2：`APP_ENV` 不能叫 `ENV`**
`ENV` 是某些 shell / 工具链的保留变量（DSH 启动时会读它），放在 `.env` 里会导致工具在这个目录下拒绝启动。所以字段叫 `app_env`。

**坑 3：list 字段的 JSON 陷阱**
见 3.4，`CORS_ORIGINS=a,b` 会炸。

**坑 4：生产校验会挡住本地调试**
`APP_ENV=prod` 时 `DEBUG=true` 直接拒绝启动。本地调试就老老实实 `APP_ENV=dev`。

---

## 自测

1. 环境变量、`.env`、默认值，三者的优先级顺序是什么？
2. 为什么 `cors_origins` 用 `str` 而不是 `list[str]`？
3. `model_validator(mode="after")` 和 `field_validator` 分别适合做什么校验？
4. 为什么配置错误要用 `SystemExit` 而不是 `RuntimeError`？
5. 测试里为什么要传 `_env_file=None`？
6. 你改了 `.env` 但应用还连旧地址，第一步查什么？