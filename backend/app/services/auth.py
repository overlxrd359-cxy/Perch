"""认证业务用例：注册、邮箱验证、登录。

事务边界在这一层：service 负责 commit / rollback，API 层只管参数与响应。
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequest, Forbidden, RateLimited, Unauthorized
from app.core.security import (
    burn_password_check,
    hash_password,
    needs_rehash,
    validate_password_strength,
    verify_password,
)
from app.core.time import utcnow
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services import verification

LOCK_THRESHOLD = 5
LOCK_MINUTES = 15


async def register_user(session: AsyncSession, payload: RegisterRequest) -> User:
    """创建 pending 用户并下发邮箱验证码。"""
    validate_password_strength(payload.password)
    email = payload.email.lower()

    # 这里刻意明确提示"已注册"：校园内部系统，可用性优先于账号枚举防护
    if await session.scalar(select(User.id).where(User.email == email)) is not None:
        raise BadRequest("该邮箱已注册", code="email_taken")
    student_no_taken = await session.scalar(
        select(User.id).where(User.student_no == payload.student_no)
    )
    if student_no_taken is not None:
        raise BadRequest("该学号已注册", code="student_no_taken")

    user = User(
        student_no=payload.student_no,
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        role=UserRole.STUDENT.value,
        status=UserStatus.PENDING.value,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        # 并发注册时唯一索引兜底；具体是邮箱还是学号冲突，回滚后无法再查，给统一文案
        await session.rollback()
        raise BadRequest("邮箱或学号已被注册", code="account_exists") from exc

    await session.refresh(user)

    code = await verification.issue_email_code(user.email)
    verification.send_verification_email(user.email, code)
    return user


async def verify_email(session: AsyncSession, email: str, code: str) -> User:
    """校验验证码并把账号置为 active。"""
    normalized = email.lower()
    await verification.consume_email_code(normalized, code)

    user = await session.scalar(select(User).where(User.email == normalized))
    if user is None:
        raise BadRequest("该邮箱未注册", code="email_not_found")

    user.email_verified = True
    if user.status == UserStatus.PENDING.value:
        user.status = UserStatus.ACTIVE.value
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate(
    session: AsyncSession,
    *,
    account: str,
    password: str,
    ip: str | None = None,
) -> User:
    """登录校验。失败文案统一，不泄露账号是否存在。"""
    normalized = account.lower() if "@" in account else account
    user = await session.scalar(
        select(User).where((User.email == normalized) | (User.student_no == account))
    )
    if user is None:
        # 账号不存在也跑一次 Argon2，抹平时序差异
        burn_password_check(password)
        raise Unauthorized("账号或密码错误")

    now = utcnow()
    if user.locked_until is not None and user.locked_until > now:
        raise RateLimited(f"尝试次数过多，请 {LOCK_MINUTES} 分钟后再试", code="account_locked")

    if user.status == UserStatus.DELETED.value:
        raise Forbidden("账号已注销", code="account_deleted")
    if user.status == UserStatus.DISABLED.value:
        raise Forbidden("账号已被禁用，请联系管理员", code="account_disabled")

    if not verify_password(password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= LOCK_THRESHOLD:
            user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            user.failed_attempts = 0
        await session.commit()
        raise Unauthorized("账号或密码错误")

    if user.status == UserStatus.PENDING.value:
        raise Forbidden("请先完成邮箱验证", code="email_not_verified")

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    user.last_login_ip = ip
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)
