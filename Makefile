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
	docker compose --env-file .env up -d postgres redis

infra-down:
	docker compose --env-file .env down

api:
	cd apps/api && uv run python main.py

api-prod:
	cd apps/api && ENVIRONMENT=production uv run python main.py

web:
	cd apps/web && npm run dev

web-prod:
	cd apps/web && npm run build && npm run start

worker:
	cd apps/api && uv run celery -A agent_yhzh.worker.celery_app worker --loglevel=INFO

test:
	cd apps/api && uv run pytest
	cd apps/web && npm run lint

lint:
	cd apps/api && uv run ruff check .
	cd apps/web && npm run lint

format:
	cd apps/api && uv run ruff format .
