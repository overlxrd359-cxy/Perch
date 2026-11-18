"""邮箱验证码的生成、存储与校验。

安全要点：
- 6 位码用 `secrets` 生成，不能用 `random`（可预测）
- Redis 只存 **哈希**，泄露 Redis 也拿不到可直接使用的码
- 15 分钟过期 + 最多 5 次尝试 + 用后即删，防止爆破
- 测试环境（APP_ENV=test）自动用内存存储，CI 不需要 Redis

邮件发送：M1 阶段没有接 SMTP，开发期把码打到日志；
接邮件服务是 M10 部署前的事，接口已经留好位置。
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from typing import Protocol

from app.core.config import get_settings
from app.core.exceptions import BadRequest
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

CODE_TTL_SECONDS = 15 * 60
MAX_ATTEMPTS = 5
_KEY_PREFIX = "auth:verify:"


class CodeStore(Protocol):
    async def set(self, key: str, value: str, ttl: int) -> None: ...

    async def get(self, key: str) -> str | None: ...

    async def delete(self, key: str) -> None: ...

    async def increment(self, key: str, ttl: int) -> int: ...


class RedisCodeStore:
    """生产 / 开发环境：验证码放 Redis，多实例共享。"""

    async def set(self, key: str, value: str, ttl: int) -> None:
        await get_redis().set(key, value, ex=ttl)

    async def get(self, key: str) -> str | None:
        value = await get_redis().get(key)
        if value is None:
            return None
        # decode_responses=True 时运行时是 str；这里兼容类型声明
        return value if isinstance(value, str) else value.decode()

    async def delete(self, key: str) -> None:
        await get_redis().delete(key)

    async def increment(self, key: str, ttl: int) -> int:
        redis = get_redis()
        count = int(await redis.incr(key))
        if count == 1:
            await redis.expire(key, ttl)
        return count


class InMemoryCodeStore:
    """测试环境：进程内存储，不依赖外部服务。"""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float]] = {}

    def reset(self) -> None:
        self._data.clear()

    async def set(self, key: str, value: str, ttl: int) -> None:
        self._data[key] = (value, time.monotonic() + ttl)

    async def get(self, key: str) -> str | None:
        item = self._data.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at < time.monotonic():
            self._data.pop(key, None)
            return None
        return value

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def increment(self, key: str, ttl: int) -> int:
        current = await self.get(key)
        count = int(current or 0) + 1
        self._data[key] = (str(count), time.monotonic() + ttl)
        return count


_memory_store = InMemoryCodeStore()


def reset_code_store() -> None:
    """测试用：清空内存里的验证码与计数。"""
    _memory_store.reset()


def get_code_store() -> CodeStore:
    if get_settings().app_env == "test":
        return _memory_store
    return RedisCodeStore()


def _code_key(email: str) -> str:
    return f"{_KEY_PREFIX}code:{email.lower()}"


def _attempts_key(email: str) -> str:
    return f"{_KEY_PREFIX}attempts:{email.lower()}"


def _hash_code(email: str, code: str) -> str:
    settings = get_settings()
    message = f"{email.lower()}:{code}".encode()
    return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()


async def issue_email_code(email: str, store: CodeStore | None = None) -> str:
    """生成并保存验证码，返回明文（仅用于开发期打印 / 发邮件）。"""
    code = f"{secrets.randbelow(1_000_000):06d}"
    backend = store or get_code_store()

    await backend.delete(_attempts_key(email))
    await backend.set(_code_key(email), _hash_code(email, code), CODE_TTL_SECONDS)
    return code


async def consume_email_code(email: str, code: str, store: CodeStore | None = None) -> None:
    """校验并作废验证码。失败抛 BadRequest，成功即删除。"""
    backend = store or get_code_store()
    code_key = _code_key(email)
    attempts_key = _attempts_key(email)

    expected = await backend.get(code_key)
    if expected is None:
        raise BadRequest("验证码已过期，请重新获取", code="code_expired")

    attempts = await backend.increment(attempts_key, CODE_TTL_SECONDS)
    if attempts > MAX_ATTEMPTS:
        await backend.delete(code_key)
        await backend.delete(attempts_key)
        raise BadRequest("验证码错误次数过多，请重新获取", code="code_attempts_exceeded")

    if not hmac.compare_digest(expected, _hash_code(email, code)):
        raise BadRequest("验证码不正确", code="code_invalid")

    await backend.delete(code_key)
    await backend.delete(attempts_key)


def send_verification_email(email: str, code: str) -> None:
    """发送验证码邮件。

    M1 阶段没有 SMTP：开发环境打到日志，生产环境只记错误（部署前必须接真实邮件服务）。
    """
    settings = get_settings()
    if settings.is_prod:
        logger.error("邮件服务尚未接入，验证码未能发送 email=%s", email)
        return
    logger.info("邮箱验证码（开发期日志）email=%s code=%s ttl=%ss", email, code, CODE_TTL_SECONDS)
