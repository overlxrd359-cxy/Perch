# 07 · Redis 异步客户端

> 对应文件：`backend/app/core/redis.py`
> 目标：客户端的生命周期怎么管，以及 M0 为什么只需要“能连、能 ping、能关”。

---

## 1. Redis 在这个项目里要干什么

M0 只建了客户端，还没用。后面每个阶段都会用到：

| 用途 | 阶段 | 用到的结构 |
| --- | --- | --- |
| 座位图缓存 | M3 | `SET key value EX 60` |
| 防超卖预扣 | M3 | Hash + Lua 原子脚本 |
| 幂等键 | M3/M9 | `SET NX EX` |
| 签到超时释放 | M4 | ZSET（score = 截止时间） |
| 分布式锁 | M4 | `SET NX PX` + 续期 |
| 限流 | M1 | Lua 滑动窗口 / 令牌桶 |
| 会话与验证码 | M1 | String + TTL |

**Redis 是性能层，不是正确性层。**
超卖最终靠 MySQL 唯一索引兜底，Redis 挂了只降性能，不能出错。这条原则从 M0 就要记住。

---

## 2. 客户端：懒加载单例

```python
from redis.asyncio import Redis

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis
```

### 2.1 用的是 `redis.asyncio`

`redis` 包同时提供同步和异步两套客户端：

```python
import redis            # 同步
from redis.asyncio import Redis   # 异步（本项目）
```

FastAPI 全异步，同步客户端会阻塞事件循环——一个慢查询能把整个进程卡住。

### 2.2 为什么懒加载

```python
_redis: Redis | None = None   # 模块导入时是 None
```

- `Redis.from_url()` 本身不发连接，但把创建推迟到第一次使用更干净
- 和数据库 engine 一样：**进程启动不依赖 Redis 可用**
- `/readyz` 才是检查点

如果改成模块顶层直接 `Redis.from_url(...)` 并 `ping()`，Redis 没起时 import 就炸，`/healthz` 也就无从谈起。

### 2.3 `decode_responses=True`

Redis 协议返回的是 bytes：

```python
# 默认
await redis.get("name")   # b'perch'

# decode_responses=True
await redis.get("name")   # 'perch'
```

项目里存的基本都是文本/JSON，统一解码省去到处 `.decode()`。
如果以后要存二进制（图片、序列化对象），单独用一个 `Redis(..., decode_responses=False)` 的客户端，别混用。

### 2.4 超时必须设

```python
socket_connect_timeout=2,
socket_timeout=2,
```

不设的话：Redis 网络半死 → 命令永远不返回 → 请求永远挂住 → 连接池被占满 → 整个服务雪崩。
**所有网络客户端都要有超时**，这是底线。

---

## 3. 健康检查与关闭

```python
async def ping_redis() -> bool:
    return bool(await get_redis().ping())


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
```

- `ping_redis()` 被 `/readyz` 调用，2 秒超时由探针层控制
- `aclose()` 关闭连接池；**不是 `close()`**。异步客户端用 `aclose()`（redis-py 5+）
- 关闭后置 `None`，下次 `get_redis()` 会重建。热重载/测试里很重要

`close_redis()` 挂在 `lifespan` 的关闭段：

```python
yield
await close_redis()
await engine.dispose()
```

---

## 4. 为什么测试用 15 号库

```python
# tests/conftest.py
os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/15"
```

Redis 默认有 16 个逻辑库（0–15），用 `/15` 隔离测试数据：

- 测试里 `flushdb` 不会清掉开发缓存
- 多个项目共用一台 Redis 时互不干扰

> 逻辑库不是真正的隔离（还是同一个进程、同一份内存），生产环境应该用独立实例或 key 前缀。

---

## 5. 后续会用到的模式（先留个印象）

### 5.1 缓存 + 主动失效

```python
async def get_seat_map(room_id: int, date: str):
    key = f"seatmap:{room_id}:{date}"
    cached = await get_redis().get(key)
    if cached:
        return json.loads(cached)

    data = await query_from_db(...)
    await get_redis().set(key, json.dumps(data), ex=60)  # 60 秒 TTL
    return data
```

预约成功后要 **主动删 key**，不能只等 TTL——否则用户取消后 60 秒内还是“已占用”。

### 5.2 分布式锁

```python
ok = await redis.set(lock_key, token, nx=True, px=10_000)  # 10 秒
if not ok:
    return  # 别的实例在跑
try:
    ...
finally:
    # 只删自己的锁（Lua 比较 token），防止误删别人的
```

### 5.3 ZSET 延迟任务

```
ZADD checkin_deadline <timestamp> <reservation_id>
```

worker 每 10 秒取 `score <= now` 的成员，处理超时未签到。比轮询全表高效得多。

---

## 6. 踩坑记录

**坑 1：事件循环绑定**
`redis.asyncio` 的连接池绑定创建它的事件循环。如果在测试里跨 loop 复用同一个全局客户端，会报 `attached to a different loop`。
测试里每个用例重建客户端，或在 `conftest` 里管理生命周期。

**坑 2：忘了 `aclose()`**
反复 `create_app()` 会攒连接。本地开发可能感觉不到，CI 跑几百个测试就会撞上 `maxclients`。

**坑 3：把 Redis 当数据库**
Redis 会丢数据（重启、淘汰策略、flush）。任何“丢了就错”的数据必须落 MySQL。

**坑 4：key 没有命名空间**
多环境共用一个 Redis 时，`seatmap:1:2026-11-16` 会互相覆盖。统一前缀（`perch:dev:...`）是基本纪律。

---

## 自测

1. `redis.asyncio` 和 `redis` 的区别？为什么 FastAPI 必须用前者？
2. 为什么客户端要懒加载？如果 import 时就 ping 会怎样？
3. `decode_responses=True` 改变了什么？
4. 为什么关闭用 `aclose()` 而不是 `close()`？
5. Redis 挂了，预约系统还能保证不超卖吗？为什么？
6. 测试为什么用 `/15` 号库？这算真正的隔离吗？