"""应用配置。

单一事实源：所有配置从环境变量 / 项目根 .env 读取，业务代码只 import get_settings()。

约定：
- 必填项缺失或非法时在导入阶段抛错（fail-fast），不带病启动。
- 生产环境额外校验：DEBUG 必须关、SECRET_KEY 不能还是示例值。
- CORS 用逗号分隔字符串存，不用 list[str]：pydantic-settings 会把 list 当 JSON 解析，
  `http://a,http://b` 这种写法会直接报错。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> core -> app -> backend -> 项目根
ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env"

# 示例密钥的标记：出现在 prod 配置里说明没换过
_DEV_SECRET_MARKERS = ("dev-only", "change-me", "changeme")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- 运行环境 ----
    app_env: Literal["dev", "test", "prod"] = "dev"
    debug: bool = False
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    # ---- 密钥（必填，缺失即拒绝启动）----
    secret_key: str = Field(min_length=32, description="JWT 签名密钥，至少 32 位")

    # ---- 依赖服务 ----
    database_url: str = (
        "mysql+asyncmy://seat:seat_dev_pwd@127.0.0.1:3306/campus_seat?charset=utf8mb4"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"
    qdrant_url: str = "http://127.0.0.1:6333"

    # ---- 跨域（逗号分隔）----
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---- 令牌 ----
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ---- AI（M7 起使用）----
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "bge-m3"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"

    @field_validator("secret_key")
    @classmethod
    def _strip_secret(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def _check_production_safety(self) -> Settings:
        if not self.is_prod:
            return self
        if self.debug:
            raise ValueError("生产环境必须 DEBUG=false")
        lowered = self.secret_key.lower()
        if any(marker in lowered for marker in _DEV_SECRET_MARKERS):
            raise ValueError("生产环境检测到示例 SECRET_KEY，请用 `openssl rand -hex 32` 重新生成")
        return self


def _format_config_error(exc: ValidationError) -> str:
    """把 pydantic 的报错整理成运维能直接照着修的提示。"""
    lines: list[str] = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error.get("loc", ()))
        lines.append(f"  - {field}: {error.get('msg', '非法值')}")
    return (
        "配置校验失败，进程拒绝启动。\n"
        "请检查项目根目录的 .env（字段清单见 .env.example）：\n"
        + "\n".join(lines)
        + "\n提示：SECRET_KEY 用 `openssl rand -hex 32` 生成；"
        "生产环境还需要 APP_ENV=prod、DEBUG=false。"
    )


@lru_cache
def _load_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    """进程内单例。测试改动环境变量后调用 get_settings.cache_clear()。"""
    try:
        return _load_settings()
    except ValidationError as exc:
        # fail-fast：与其带着半套配置启动、在第一个请求才炸，不如现在退出并说清楚缺什么
        raise SystemExit(_format_config_error(exc)) from None
