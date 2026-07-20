.PHONY: setup setup-local infra-up infra-down api api-prod web web-prod worker test lint format

setup:
	test -f .env || cp .env.example .env
	test -f apps/api/.env || cp .env.example apps/api/.env
	test -f apps/web/.env.local || cp apps/web/.env.local.example apps/web/.env.local
	cd apps/api && uv sync
	cd apps/web && npm install

setup-local:
	test -f apps/api/.env || cp apps/api/.env.sqlite.example apps/api/.env
	test -f apps/web/.env.local || cp apps/web/.env.local.example apps/web/.env.local
	cd apps/api && uv sync
	cd apps/web && npm install

infra-up:
	docker compose --env-file .env up -d postgres redis minio

infra-down:
	docker compose --env-file .env down

api:
	cd apps/api && uv run python main.py

api-prod:
	cd apps/api && uv run uvicorn agent_yhzh.app:app --host 0.0.0.0 --port 8123

web:
	cd apps/web && npm run dev

web-prod:
	cd apps/web && npm run build && npm run start

worker:
	cd apps/api && uv run celery -A agent_yhzh.worker.celery_app worker --loglevel=INFO

test:
	cd apps/api && uv run ruff check . && uv run mypy agent_yhzh --ignore-missing-imports && uv run pytest
	cd apps/web && npm run lint && npm run build

lint:
	cd apps/api && uv run ruff check .
	cd apps/web && npm run lint

format:
	cd apps/api && uv run ruff format .
