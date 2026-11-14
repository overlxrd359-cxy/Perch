.DEFAULT_GOAL := help
SHELL := /bin/bash

help: ## 显示可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## 启动 MySQL / Redis / Qdrant
	docker compose up -d
	@docker compose ps

down: ## 停止并移除容器（保留数据卷）
	docker compose down

reset: ## 停止并删除数据卷（危险：清空所有数据）
	docker compose down -v

ps: ## 查看依赖服务状态
	docker compose ps

logs: ## 跟踪依赖服务日志
	docker compose logs -f --tail=100

backend: ## 启动后端开发服务器（热重载）
	cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend: ## 启动前端开发服务器
	cd frontend && npm run dev

test: ## 运行后端测试
	cd backend && pytest -q

lint: ## 运行 ruff 与 mypy
	cd backend && ruff check . && ruff format --check . && mypy app

fmt: ## 自动格式化
	cd backend && ruff format . && ruff check --fix .

migrate: ## 生成迁移（用法：make migrate m="add users"）
	cd backend && alembic revision --autogenerate -m "$(m)"

upgrade: ## 应用迁移到最新
	cd backend && alembic upgrade head

downgrade: ## 回滚一个版本
	cd backend && alembic downgrade -1

health: ## 检查后端健康状态
	curl -s http://127.0.0.1:8000/healthz | python3 -m json.tool

.PHONY: help up down reset ps logs backend frontend test lint fmt migrate upgrade downgrade health