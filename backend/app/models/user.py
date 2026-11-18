"""用户模型。

字段按方案 v2 §3.2 一次建全：role / status / credit_score / 锁定字段 / MFA 字段
现在只用到一部分，但后续 M2（角色）、M4（信用与禁约）都长在这张表上，
分阶段 ALTER 的成本比一次建高。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IntPKMixin, TimestampMixin
from app.models.enums import UserRole, UserStatus


class User(IntPKMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('student','reviewer','admin','super_admin')", name="ck_users_role"
        ),
        CheckConstraint(
            "status IN ('pending','active','disabled','deleted')", name="ck_users_status"
        ),
    )

    # ---- 身份 ----
    student_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))

    # ---- 凭证 ----
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # ---- 权限与状态 ----
    role: Mapped[str] = mapped_column(String(20), default=UserRole.STUDENT.value, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=UserStatus.PENDING.value, nullable=False
    )

    # ---- 信用（M4 使用）----
    credit_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    banned_until: Mapped[datetime | None] = mapped_column(DateTime)

    # ---- 登录安全 ----
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    mfa_secret: Mapped[str | None] = mapped_column(String(64))
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_login_ip: Mapped[str | None] = mapped_column(String(45))


__all__ = ["User"]
