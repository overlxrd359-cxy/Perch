"""API 层公共依赖。"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Forbidden, Unauthorized
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.enums import UserStatus
from app.models.user import User

# auto_error=False：缺 token 时由我们自己抛 401，而不是 FastAPI 默认的 403
_bearer_scheme = HTTPBearer(auto_error=False, description="Bearer access token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """解析 access token 并加载当前用户。

    注意这里只做认证（你是谁）；权限点校验（能不能干）由 M1-10 的 require() 负责。
    """
    if credentials is None:
        raise Unauthorized()

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise Unauthorized("无效的登录凭证", code="token_invalid") from exc

    user = await session.get(User, user_id)
    if user is None:
        raise Unauthorized("登录状态已失效", code="user_not_found")
    if user.status != UserStatus.ACTIVE.value:
        raise Forbidden("账号不可用", code="account_unavailable")
    return user
