"""应用配置。

设计要点：
1. 全部配置集中在这里，禁止在业务代码里读 os.environ。
2. **fail-fast**：缺必填项直接拒绝启动，而不是运行到一半才报错。
3. 生产环境禁止使用示例密钥。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> 项目根目录
ROOT_DIR = Path(__file__).resolve().parents[3]

# 示例密钥前缀，用于生产环境拦截
_DEV_SECRET_PREFIX = "dev-only"  # noqa: S105 - 这是用于拦截的前缀，不是密码


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- 基础 ----
    app_name: str = "Campus Seat"
    app_version: str = "0.1.0"
    env: Literal["dev", "test", "prod"] = "dev"
    debug: bool = True

    # ---- 安全 ----
    secret_key: str = Field(..., min_length=32, description="JWT 签名密钥，至少 32 位")
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ---- 依赖服务 ----
    database_url: str = (
        "mysql+asyncmy://seat:seat_dev_pwd@127.0.0.1:3306/campus_seat?charset=utf8mb4"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"
    qdrant_url: str = "http://127.0.0.1:6333"

    # ---- 跨域：逗号分隔的字符串，避免 pydantic 对 list 做 JSON 解析 ----
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---- LLM（M7 使用，暂时留空不影响启动） ----
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @model_validator(mode="after")
    def _guard_production(self) -> Settings:
        if self.env == "prod":
            if self.secret_key.startswith(_DEV_SECRET_PREFIX):
                raise ValueError(
                    "生产环境禁止使用示例 SECRET_KEY，请用 `openssl rand -hex 32` 生成"
                )
            if self.debug:
                raise ValueError("生产环境必须设置 DEBUG=false")
        return self


def _load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        missing = [str(err["loc"][0]) for err in exc.errors() if err["type"] == "missing"]
        hint = (
            f"缺少必需配置项: {', '.join(missing)}。\n"
            f"请执行: cp {ROOT_DIR / '.env.example'} {ROOT_DIR / '.env'} 后填写。"
        )
        raise SystemExit(f"[config] 启动失败\n{hint}") from exc


@lru_cache
def get_settings() -> Settings:
    return _load_settings()


settings = get_settings()
