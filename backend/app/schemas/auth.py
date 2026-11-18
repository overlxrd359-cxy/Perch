"""认证相关请求 / 响应模型。

约定：
- 所有请求 `extra="forbid"`：多传字段直接 422，不给"偷偷塞 role"的机会
- 密码长度只做 1–128 的硬边界，具体强度由 core.security 判定（单一事实源）
- 响应模型不直接返回 ORM 对象，避免把 password_hash 带出去
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import PASSWORD_MAX_LENGTH, STUDENT_NO_PATTERN


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    student_no: str = Field(
        min_length=8,
        max_length=12,
        pattern=STUDENT_NO_PATTERN.pattern,
        description="学号，8–12 位数字",
        examples=["2023123456"],
    )
    name: str = Field(min_length=2, max_length=64, description="真实姓名", examples=["张三"])
    email: EmailStr = Field(description="用于接收验证码")
    password: str = Field(
        min_length=1,
        max_length=PASSWORD_MAX_LENGTH,
        description="至少 10 位，需含字母和数字，不能是常见弱口令",
    )

    @field_validator("name")
    @classmethod
    def _reject_control_chars(cls, value: str) -> str:
        if any(ord(char) < 32 for char in value):
            raise ValueError("姓名不能包含控制字符")
        return value


class RegisterResponse(BaseModel):
    message: str
    email: EmailStr
    expires_in: int


class MessageResponse(BaseModel):
    message: str


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$", description="6 位邮箱验证码")


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    account: str = Field(
        min_length=1,
        max_length=128,
        description="学号或邮箱",
        examples=["2023123456"],
    )
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_no: str
    name: str
    email: str
    email_verified: bool
    role: str
    status: str
    credit_score: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 固定值，不是密码
    expires_in: int
    user: UserOut
