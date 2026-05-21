.PHONY: help install test lint typecheck ci api web

help:
	@echo "make install     - install backend + frontend deps"
	@echo "make test        - run backend tests"
	@echo "make lint        - run ruff"
	@echo "make typecheck   - run mypy"
	@echo "make ci          - lint + typecheck + test"
	@echo "make api         - run FastAPI dev server"
	@echo "make web         - run Next.js dev server"

install:
	cd apps/api && uv sync
	cd apps/web && pnpm install

test:
	cd apps/api && uv run pytest -v

lint:
	cd apps/api && uv run ruff check src tests

typecheck:
	cd apps/api && uv run mypy src

ci: lint typecheck test

api:
	cd apps/api && uv run uvicorn src.api.main:app --reload --port 8000

web:
	cd apps/web && pnpm dev
