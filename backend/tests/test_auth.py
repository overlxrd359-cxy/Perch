"""M1W1 认证核心验收测试。

覆盖 PLAN 里的四条验收：
- 弱口令被拒
- 连续 6 次错密码 → 锁定，正确密码也进不去
- 登录失败文案不区分"账号不存在"和"密码错误"
- access 过期后接口返回 401
外加注册落库、邮箱验证、重复注册等基础行为。
"""

from __future__ import annotations

from datetime import timedelta

import httpx
import jwt
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import JWT_ALGORITHM
from app.core.time import now_utc
from app.models.enums import UserStatus
from app.models.user import User

REGISTER_PAYLOAD: dict[str, str] = {
    "student_no": "2023123456",
    "name": "张三",
    "email": "zhangsan@example.edu.cn",
    "password": "studyroom2026",
}
PASSWORD = REGISTER_PAYLOAD["password"]


async def _register(
    client: httpx.AsyncClient, **overrides: str
) -> tuple[httpx.Response, dict[str, str]]:
    payload = {**REGISTER_PAYLOAD, **overrides}
    response = await client.post("/api/v1/auth/register", json=payload)
    return response, payload


async def _activate(
    client: httpx.AsyncClient, codes: list[tuple[str, str]], payload: dict[str, str]
) -> httpx.Response:
    code = codes[-1][1]
    return await client.post(
        "/api/v1/auth/verify-email", json={"email": payload["email"], "code": code}
    )


async def _login(client: httpx.AsyncClient, account: str, password: str) -> httpx.Response:
    return await client.post("/api/v1/auth/login", json={"account": account, "password": password})


async def _active_user(client: httpx.AsyncClient, codes: list[tuple[str, str]]) -> dict[str, str]:
    _, payload = await _register(client)
    verify = await _activate(client, codes, payload)
    assert verify.status_code == 200
    return payload


async def test_register_creates_pending_user(
    client: httpx.AsyncClient,
    captured_codes: list[tuple[str, str]],
    db_session: AsyncSession,
) -> None:
    response, payload = await _register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == payload["email"]
    assert body["expires_in"] == 900
    assert captured_codes and captured_codes[-1][0] == payload["email"]

    user = await db_session.scalar(select(User).where(User.email == payload["email"]))
    assert user is not None
    assert user.status == UserStatus.PENDING.value
    assert user.email_verified is False
    assert user.role == "student"
    assert user.password_hash.startswith("$argon2id$")
    assert payload["password"] not in user.password_hash


@pytest.mark.parametrize("weak_password", ["12345678", "abcdefghij", "password123"])
async def test_register_rejects_weak_password(
    client: httpx.AsyncClient,
    captured_codes: list[tuple[str, str]],
    weak_password: str,
) -> None:
    response, _ = await _register(client, password=weak_password)

    assert response.status_code == 400
    assert response.json()["code"] == "weak_password"


@pytest.mark.parametrize("bad_student_no", ["abc1234567", "123", "1234567890123"])
async def test_register_rejects_invalid_student_no(
    client: httpx.AsyncClient,
    captured_codes: list[tuple[str, str]],
    bad_student_no: str,
) -> None:
    response, _ = await _register(client, student_no=bad_student_no)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_register_rejects_duplicate_email(
    client: httpx.AsyncClient, captured_codes: list[tuple[str, str]]
) -> None:
    first, _ = await _register(client)
    assert first.status_code == 201

    second, _ = await _register(client, student_no="2023123457", email=REGISTER_PAYLOAD["email"])

    assert second.status_code == 400
    assert second.json()["code"] == "email_taken"
    assert second.json()["message"] == "该邮箱已注册"


async def test_register_rejects_duplicate_student_no(
    client: httpx.AsyncClient, captured_codes: list[tuple[str, str]]
) -> None:
    first, _ = await _register(client)
    assert first.status_code == 201

    second, _ = await _register(
        client, email="another@example.edu.cn", student_no=REGISTER_PAYLOAD["student_no"]
    )

    assert second.status_code == 400
    assert second.json()["code"] == "student_no_taken"


async def test_login_before_verify_is_forbidden(
    client: httpx.AsyncClient, captured_codes: list[tuple[str, str]]
) -> None:
    _, payload = await _register(client)

    response = await _login(client, payload["student_no"], PASSWORD)

    assert response.status_code == 403
    assert response.json()["code"] == "email_not_verified"


async def test_verify_email_activates_and_login_works(
    client: httpx.AsyncClient, captured_codes: list[tuple[str, str]]
) -> None:
    _, payload = await _register(client)
    verify = await _activate(client, captured_codes, payload)

    assert verify.status_code == 200
    assert "可以登录" in verify.json()["message"]

    login = await _login(client, payload["student_no"], PASSWORD)
    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["status"] == "active"

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["student_no"] == payload["student_no"]


async def test_login_error_message_does_not_leak_account_existence(
    client: httpx.AsyncClient, captured_codes: list[tuple[str, str]]
) -> None:
    await _active_user(client, captured_codes)

    wrong_password = await _login(client, REGISTER_PAYLOAD["student_no"], "wrong-password-1")
    unknown_account = await _login(client, "2099000000", PASSWORD)

    assert wrong_password.status_code == 401
    assert unknown_account.status_code == 401
    assert wrong_password.json()["message"] == unknown_account.json()["message"] == "账号或密码错误"


async def test_lockout_after_five_failures_blocks_correct_password(
    client: httpx.AsyncClient, captured_codes: list[tuple[str, str]]
) -> None:
    payload = await _active_user(client, captured_codes)

    for _ in range(5):
        response = await _login(client, payload["student_no"], "wrong-password-1")
        assert response.status_code == 401

    sixth = await _login(client, payload["student_no"], PASSWORD)

    assert sixth.status_code == 429
    assert sixth.json()["code"] == "account_locked"


async def test_expired_access_token_is_rejected(
    client: httpx.AsyncClient,
    captured_codes: list[tuple[str, str]],
    db_session: AsyncSession,
) -> None:
    payload = await _active_user(client, captured_codes)
    user = await db_session.scalar(select(User).where(User.email == payload["email"]))
    assert user is not None

    expired_at = now_utc() - timedelta(minutes=1)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "role": user.role,
            "type": "access",
            "iat": int((expired_at - timedelta(minutes=15)).timestamp()),
            "exp": int(expired_at.timestamp()),
        },
        get_settings().secret_key,
        algorithm=JWT_ALGORITHM,
    )

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["code"] == "token_expired"


async def test_me_requires_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
