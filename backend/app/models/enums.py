"""领域枚举。

角色 / 状态在数据库里用 VARCHAR(20) 存，不用 MySQL 原生 ENUM：
原生 ENUM 加值要 ALTER TABLE，迁移和回滚都麻烦；约束交给 CHECK + 应用层枚举。
"""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    STUDENT = "student"
    REVIEWER = "reviewer"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(StrEnum):
    PENDING = "pending"  # 已注册，待邮箱验证
    ACTIVE = "active"
    DISABLED = "disabled"  # 管理员禁用
    DELETED = "deleted"  # 注销（软删除）
