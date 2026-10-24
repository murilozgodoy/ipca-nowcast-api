.PHONY: help install up down logs test lint format typecheck migrate dev clean fixtures

help:
	@echo "Targets:"
	@echo "  install    - uv sync (install deps incl. dev)"
	@echo "  up         - start Postgres via docker compose"
	@echo "  down       - stop Postgres"
	@echo "  logs       - follow Postgres logs"
	@echo "  migrate    - alembic upgrade head"
	@echo "  dev        - run API in reload mode"
	@echo "  test       - run pytest with coverage"
	@echo "  lint       - ruff check"
	@echo "  format     - ruff format"
	@echo "  typecheck  - mypy src"
	@echo "  fixtures   - macro seed --fixtures"

install:
	uv sync --all-extras

up:
	docker compose up -d postgres

down:
	docker compose down

logs:
	docker compose logs -f postgres

migrate:
	uv run alembic upgrade head

dev:
	uv run uvicorn ipca_nowcast.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest --cov=src/ipca_nowcast --cov-report=term-missing

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

typecheck:
	uv run mypy src

fixtures:
	uv run macro seed --fixtures

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
