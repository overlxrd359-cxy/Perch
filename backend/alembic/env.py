"""Alembic 环境。

当前为最小可运行版本：从环境变量 / 项目根 .env 读取 DATABASE_URL。

TODO(M0)：
- [ ] 改为复用 app.core.config.settings，避免两处解析
- [ ] 注册 target_metadata = Base.metadata（需要 app.db.base 先实现）
- [ ] 打开 compare_type / compare_server_default
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import MetaData, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

# 项目根目录：backend/alembic/env.py -> backend -> 项目根
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

if not os.environ.get("DATABASE_URL") and _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        if _line.startswith("DATABASE_URL="):
            os.environ["DATABASE_URL"] = _line.split("=", 1)[1].strip()
            break

_database_url = os.environ.get(
    "DATABASE_URL",
    "mysql+asyncmy://seat:seat_dev_pwd@127.0.0.1:3306/campus_seat?charset=utf8mb4",
)
# 密码里的 % 会被 configparser 当成插值
config.set_main_option("sqlalchemy.url", _database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# TODO(M0)：替换为 from app.db.base import Base; target_metadata = Base.metadata
target_metadata: MetaData = MetaData()


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()