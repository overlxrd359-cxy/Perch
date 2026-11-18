"""认证接口。

M1W1 范围：注册 → 邮箱验证 → 登录 → 拿 access token 访问 /me。
refresh token、登出、会话列表属于 M1-6 ～ M1-9。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserOut,
    VerifyEmailRequest,
)
from app.services import auth as auth_service
from app.services import verification

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> RegisterResponse:
    """注册后账号为 pending，必须完成邮箱验证才能登录。"""
    user = await auth_service.register_user(session, payload)
    return RegisterResponse(
        message="验证码已发送，请查收邮箱",
        email=user.email,
        expires_in=verification.CODE_TTL_SECONDS,
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    user = await auth_service.verify_email(session, payload.email, payload.code)
    return MessageResponse(message=f"邮箱验证成功，{user.student_no} 现在可以登录了")


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    client_ip = request.client.host if request.client else None
    user = await auth_service.authenticate(
        session,
        account=payload.account,
        password=payload.password,
        ip=client_ip,
    )
    settings = get_settings()
    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    """受保护接口：能返回自己，说明 access token 链路是通的。"""
    return UserOut.model_validate(current_user)
