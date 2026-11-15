# 06 · 数据库与 Alembic 迁移

> 对应文件：`backend/app/db/session.py`、`backend/app/db/base.py`、`backend/app/core/time.py`、`backend/alembic/env.py`
> 目标：理解异步 ORM 的连接/会话/事务，以及迁移为什么不能手改库。

---

## 1. 先理清几个名词

| 名词 | 是什么 | 本项目 |
| --- | --- | --- |
| 驱动 | 和数据库说话的底层库 | `asyncmy`（MySQL 的异步驱动） |
| DSN | 连接串 | `mysql+asyncmy://user:pwd@host:port/db?charset=utf8mb4` |
| Engine | 连接池 + 方言，进程内一个 | `create_async_engine(...)` |
| Session | 一次工作单元，管事务和对象缓存 | `async_sessionmaker(...)` |
| ORM | 把表映射成 Python 类 | `Mapped[...]` / `mapped_column` |

DSN 拆开看：

```
mysql+asyncmy://seat:seat_dev_pwd@127.0.0.1:3307/campus_seat?charset=utf8mb4
└─┬─┘ └───┬───┘   └┬─┘ └─────┬────┘ └──┬──┘ └───┬────┘ └───┬───┘
 方言    驱动     用户      密码       主机     端口        库
```

`charset=utf8mb4` 不能省：MySQL 的 `utf8` 是 3 字节，存不了 emoji；`utf8mb4` 才是真 UTF-8。

---

## 2. Engine：连接池与“懒连接”

```python
engine = create_async_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=10,
    echo=False,
)
```

### 2.1 创建 engine 不会连数据库

`create_async_engine()` 只是解析 DSN、准备方言和池配置，**不发起 TCP 连接**。
第一次真正需要连接（执行 SQL / `engine.connect()`）时才连。

这直接支撑了 M0 的验收：MySQL 没起，进程也能启动，`/readyz` 负责报 503。

### 2.2 池参数

| 参数 | 作用 | 为什么这么设 |
| --- | --- | --- |
| `pool_size=5` | 常驻连接数 | 开发够用，生产按并发调 |
| `max_overflow=10` | 峰值可临时多开 | 最多 15 个连接，防止打爆 MySQL |
| `pool_pre_ping=True` | 取连接前先 ping | MySQL 会主动断开空闲连接，不 ping 会拿到死连接 |
| `pool_recycle=1800` | 连接最多复用 30 分钟 | 必须小于 MySQL 的 `wait_timeout`（默认 8 小时，但云数据库常改短） |
| `echo=False` | 不打印 SQL | 调试时改 True，但别提交 |

`pool_pre_ping` 是性价比最高的一个参数：多一次轻量 ping，换来“不会随机报 connection lost”。

---

## 3. Session：一个请求一个工作单元

```python
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
```

### 3.1 `expire_on_commit=False` 为什么重要

默认 `True`：commit 之后，所有对象的属性被标记为“过期”，下次访问会**重新查库**。

在异步 ORM 里这很危险：

```python
reservation = Reservation(...)
await session.commit()
print(reservation.id)   # 触发一次隐式查询
```

隐式查询需要一个 await 上下文，而属性访问是同步的 → 抛 `MissingGreenlet`。这个报错非常难懂，新手常卡半天。

设 `False` 后，commit 不会让对象失效，`reservation.id` 直接读内存。代价是对象可能持有旧数据——对“请求结束就丢弃”的场景完全可接受。

### 3.2 `autoflush=False`

默认 `True` 时，任何查询前会先把挂起的对象 flush 到数据库。调试时经常出现“我没 commit 怎么就写进去了”。

关掉后，写入时机完全由你控制：

```python
session.add(obj)
await session.flush()    # 显式写入，拿自增 ID，但不开事务提交
await session.commit()   # 提交
```

### 3.3 依赖注入

```python
async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

- `async with` 保证 session 一定被关闭（连接还给池）
- `yield` 之前是“进入请求”，之后是“请求结束”
- 异常时回滚：否则这个 session 可能带着半截事务被复用

**谁 commit？** service 层。`get_session` 不自动 commit，因为一个请求里可能有多段逻辑，提交时机是业务决定。

用法：

```python
@router.get("/reservations/{id}")
async def get_reservation(id: int, session: AsyncSession = Depends(get_session)):
    ...
```

---

## 4. ORM 基类与 Mixin

```python
class Base(DeclarativeBase):
    """所有模型的声明式基类；Alembic 的 target_metadata 指向 Base.metadata。"""
```

SQLAlchemy 2.0 用 `DeclarativeBase` 替代旧的 `declarative_base()`。`Base.metadata` 里收集了所有继承它的表定义，Alembic 靠它做 diff。

### 4.1 类型化字段

```python
class IntPKMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
```

- `Mapped[int]` 是类型注解，mypy 和 IDE 能识别 `obj.id` 是 int
- `mapped_column(...)` 是列定义
- `BigInteger` 自增主键：`INT` 上限 21 亿，预约系统的 slot 表很容易超
- `default=utcnow` 是 Python 侧默认值（插入时算）；`onupdate=utcnow` 在 UPDATE 时自动刷新

> Mixin 里的列会被每个继承它的模型复制一份。`Base` + 两个 Mixin 的组合写法：
>
> ```python
> class User(IntPKMixin, TimestampMixin, Base):
>     __tablename__ = "users"
>     ...
> ```

### 4.2 时间为什么存 naive UTC

```python
def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
```

MySQL 的 `DATETIME` 不带时区。存 aware 时间会被驱动告警/截断，存本地时间则会在换时区、夏令时、服务器迁移时全乱。

规则：

- **入库**：naive UTC
- **展示**：`to_local()` 转 `Asia/Shanghai`
- **业务代码**：禁止裸 `datetime.now()`，只从 `app/core/time.py` 走

这条规则从 M0 定死，是因为 M3 的 slot 计算会重度依赖时间，后改成本极高。

---

## 5. Alembic：迁移即代码

### 5.1 为什么不能手改库

```
开发机: 我手动 ALTER TABLE 加了字段
测试库: 忘了加 → 接口 500
生产库: 更不敢动 → 上线失败
```

迁移文件进 git 后：

- 每个环境的表结构都由同一串迁移推导出来
- 代码回滚时迁移也能回滚
- Code Review 能看到“这次改了哪些列”

### 5.2 env.py 做了三件事

```python
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
target_metadata = Base.metadata
```

1. **URL 只从 config 读**：不在 `alembic.ini` 和 `.env` 两处各写一份，避免两边不一致
2. **`replace("%", "%%")`**：如果密码里有 `%`，configparser 会把它当插值语法，必须转义
3. **`target_metadata = Base.metadata`**：告诉 autogenerate “模型长这样”

### 5.3 autogenerate 的原理

```bash
make migrate m="add users"
# 等价于 alembic revision --autogenerate -m "add users"
```

它做的事：

1. 连上数据库，读当前表结构
2. 读 `Base.metadata` 里的模型定义
3. diff 出差异，生成 `upgrade()` / `downgrade()` 两个函数

**前提：模型必须被 import 过**，否则 `Base.metadata` 里没有它。
所以 `app/db/init_models.py` 的职责就是把所有模型 import 一遍（M1 起使用）。

### 5.4 compare_type 与 compare_server_default

```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    compare_type=True,
    compare_server_default=True,
)
```

不开的话，autogenerate 只比较“表/列有没有增删”，**不比较类型和默认值**：

- `VARCHAR(32)` 改成 `VARCHAR(64)` → 检测不到
- 默认值从 `0` 改成 `100` → 检测不到

这两个开关打开后，`alembic check` 才能真正回答“模型和库是否一致”。

### 5.5 常用命令

```bash
make migrate m="add users"   # 生成迁移（要 review！）
make upgrade                 # 应用到最新
make downgrade               # 回滚一个版本
```

> **autogenerate 生成的迁移必须人工看一遍**。它不知道：
> - 数据怎么迁移（加非空列要不要填默认值）
> - 索引名是否合理
> - 要不要 `CONCURRENTLY` 建索引
>
> 它只是个草稿生成器，不是自动驾驶。

M0 阶段 `Base.metadata` 是空的，所以：

```bash
alembic upgrade head   # 什么都不做
alembic check          # No new upgrade operations detected.
```

这是正常的，等 M1 有 `users` 表后才会有第一个迁移。

---

## 6. 踩坑记录

**坑 1：`cryptography` 缺失**
MySQL 8 默认 `caching_sha2_password`，asyncmy 需要它做 RSA 公钥交换：

```
RuntimeError: 'cryptography' package is required for sha256_password or caching_sha2_password
```

解决：`pip install cryptography`，并写进 `pyproject.toml`。

**坑 2：端口被系统 MySQL 占用**
容器映射 3306 失败。本地改 3307，`.env` 的 `DATABASE_URL` 同步改。

**坑 3：shell 环境变量覆盖 `.env`**
改完 `.env` 发现还连 3306，因为 shell 里残留 `DATABASE_URL`。先 `env | grep DATABASE_URL`。

**坑 4：`MissingGreenlet`**
异步 ORM 里触发隐式 IO（懒加载、commit 后访问属性）。`expire_on_commit=False` + 查询时显式 `selectinload`/`joinedload` 可以避免。

**坑 5：`alembic check` 说 no changes，但其实模型没被 import**
autogenerate 只认识 `Base.metadata` 里的东西。新增模型后要确认它在 `init_models.py` 里被 import。

---

## 自测

1. `create_async_engine` 会立刻连数据库吗？这带来什么好处？
2. `pool_pre_ping` 和 `pool_recycle` 分别解决什么问题？
3. `expire_on_commit=False` 为什么能避免 `MissingGreenlet`？
4. `get_session` 为什么不在 finally 里 commit？
5. 时间为什么存 naive UTC 而不是本地时间或带时区时间？
6. Alembic 的 `target_metadata` 是什么？模型没被 import 会怎样？
7. `compare_type=True` 不开会漏掉什么变更？