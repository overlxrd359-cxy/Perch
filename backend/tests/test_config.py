"""配置系统：fail-fast 与生产环境安全校验。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def test_settings_loads_from_env() -> None:
    settings = get_settings()

    assert settings.app_env == "test"
    assert settings.is_prod is False
    assert settings.cors_origin_list == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_missing_secret_key_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert "secret_key" in str(exc_info.value)


def test_secret_key_shorter_than_32_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, secret_key="too-short")


def test_cors_origins_split_and_trim() -> None:
    settings = Settings(
        _env_file=None,
        secret_key="x" * 48,
        cors_origins="http://a.test, http://b.test ,",
    )

    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_production_rejects_debug() -> None:
    with pytest.raises(ValidationError, match="DEBUG"):
        Settings(_env_file=None, app_env="prod", debug=True, secret_key="x" * 48)


def test_production_rejects_example_secret() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            _env_file=None,
            app_env="prod",
            debug=False,
            secret_key="dev-only-secret-key-change-me-0123456789abcdef",
        )
