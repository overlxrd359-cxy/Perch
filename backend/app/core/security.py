"""密码哈希与 JWT。

密码策略（NIST SP 800-63B 思路）：
- 只卡长度、字符种类、弱口令表；不强制"必须大写 + 符号"
- 复杂度规则会逼用户写出 `Password1!` 这种可预测密码，收益为负
- Argon2id 参数取 64MB / 3 轮，单次约几十毫秒，兼顾抗爆破与登录体验

JWT：
- 只签 access token（15 分钟）；refresh 在 M1-6 单独做
- 算法固定 HS256，解码时显式指定，禁止 `alg=none` 之类的降级攻击
"""

from __future__ import annotations

import re
from datetime import timedelta
from functools import lru_cache
from typing import Any
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.core.exceptions import BadRequest, Unauthorized
from app.core.time import now_utc

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128
STUDENT_NO_PATTERN = re.compile(r"^\d{8,12}$")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - 这是令牌类型标签，不是密码

# 只放最常见的弱口令，真正的大字典等 M9 再引；这里挡住"随手一输"
_WEAK_PASSWORDS = frozenset(
    {
        "1234567890",
        "12345678910",
        "password123",
        "password1234",
        "qwerty12345",
        "abc1234567",
        "1111111111",
        "0000000000",
        "iloveyou123",
        "admin12345",
        "student123",
        "a123456789",
    }
)

# 内存 64MB、3 轮、4 并行度：约 30–60ms/次
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bool(_hasher.verify(password_hash, password))
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """Argon2 参数升级后，登录成功时顺带重算旧哈希。"""
    return bool(_hasher.check_needs_rehash(password_hash))


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """账号不存在时也跑一次校验，抹平时序差异。

    否则攻击者可以通过响应时间区分"账号不存在"（快速返回）和"密码错误"（跑完 Argon2）。
    """
    return _hasher.hash("timing-defense-dummy-value")


def burn_password_check(password: str) -> None:
    verify_password(password, _dummy_hash())


def validate_password_strength(password: str) -> None:
    """密码策略的唯一事实源。前端提示文案与这里保持一致。"""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise BadRequest(f"密码至少 {PASSWORD_MIN_LENGTH} 位", code="weak_password")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise BadRequest(f"密码不能超过 {PASSWORD_MAX_LENGTH} 位", code="weak_password")
    if any(ord(char) < 32 for char in password):
        raise BadRequest("密码不能包含控制字符", code="weak_password")
    if not any(char.isalpha() for char in password) or not any(char.isdigit() for char in password):
        raise BadRequest("密码需同时包含字母和数字", code="weak_password")
    if password.lower() in _WEAK_PASSWORDS:
        raise BadRequest("这个密码太常见了，换一个", code="weak_password")


def create_access_token(*, subject: str, role: str) -> str:
    settings = get_settings()
    issued_at = now_utc()
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(issued_at.timestamp()),
        "exp": int(
            (issued_at + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()
        ),
        "jti": uuid4().hex,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized("登录已过期，请重新登录", code="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise Unauthorized("无效的登录凭证", code="token_invalid") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise Unauthorized("无效的登录凭证", code="token_invalid")
    return payload
