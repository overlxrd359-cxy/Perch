# 后端生产镜像。
#
# 设计要点：
# 1. 非 root 运行（appuser, uid 10001）
# 2. 依赖在构建期装好，运行期不联网
# 3. 只暴露 8000，由前置 Caddy 负责 TLS

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# asyncmy / cryptography 在无预编译 wheel 时需要编译器
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --upgrade pip \
    && pip install . \
    && apt-get purge -y --auto-remove build-essential

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# 2 worker：2C4G 上够用；再加要看 CPU 核数，不是越多越好
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]