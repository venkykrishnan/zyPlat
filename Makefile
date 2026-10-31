.PHONY: help db-up db-down db-migrate db-downgrade db-verify format lint type-check check fix test test-cov

DB_CONTAINER ?= zyplat-postgres
DB_PORT ?= 5432
DB_USER ?= postgres
DB_PASSWORD ?= postgres
DB_NAME ?= zyplat
DB_IMAGE ?= postgres:16

DATABASE_URL ?= postgresql+psycopg://$(DB_USER):$(DB_PASSWORD)@localhost:$(DB_PORT)/$(DB_NAME)
PSQL_URL ?= postgresql://$(DB_USER):$(DB_PASSWORD)@localhost:$(DB_PORT)/$(DB_NAME)
ALEMBIC ?= alembic -c backend/alembic.ini

help:
	@echo "Available targets:"
	@echo ""
	@echo "Database:"
	@echo "  make db-up         # Start local Postgres container (or start existing one)"
	@echo "  make db-down       # Stop local Postgres container"
	@echo "  make db-migrate    # Run Alembic upgrade head"
	@echo "  make db-downgrade  # Run Alembic downgrade -1"
	@echo "  make db-verify     # Run schema verification SQL checks"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format        # Format code with black"
	@echo "  make lint          # Run ruff linter"
	@echo "  make type-check    # Run mypy type checker"
	@echo "  make check         # Run all code quality checks"
	@echo "  make fix           # Auto-fix linting issues"
	@echo ""
	@echo "Testing:"
	@echo "  make test          # Run all tests"
	@echo "  make test-cov      # Run tests with coverage report"
	@echo ""
	@echo "Configurable variables:"
	@echo "  DB_CONTAINER=$(DB_CONTAINER)"
	@echo "  DB_PORT=$(DB_PORT)"
	@echo "  DB_USER=$(DB_USER)"
	@echo "  DB_PASSWORD=<hidden>"
	@echo "  DB_NAME=$(DB_NAME)"
	@echo "  DATABASE_URL=$(DATABASE_URL)"

db-up:
	@command -v docker >/dev/null 2>&1 || { echo "docker is required"; exit 1; }
	@if docker ps -a --format '{{.Names}}' | grep -qx '$(DB_CONTAINER)'; then \
		echo "Container $(DB_CONTAINER) already exists. Starting..."; \
		docker start $(DB_CONTAINER) >/dev/null; \
	else \
		echo "Creating container $(DB_CONTAINER)..."; \
		docker run -d --name $(DB_CONTAINER) \
			-p $(DB_PORT):5432 \
			-e POSTGRES_USER=$(DB_USER) \
			-e POSTGRES_PASSWORD=$(DB_PASSWORD) \
			-e POSTGRES_DB=$(DB_NAME) \
			$(DB_IMAGE) >/dev/null; \
	fi
	@echo "Waiting for Postgres readiness..."
	@for i in $$(seq 1 30); do \
		if docker exec $(DB_CONTAINER) pg_isready -U $(DB_USER) -d $(DB_NAME) >/dev/null 2>&1; then \
			echo "Postgres is ready on localhost:$(DB_PORT)"; \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "Postgres did not become ready in time"; \
	exit 1

db-down:
	@command -v docker >/dev/null 2>&1 || { echo "docker is required"; exit 1; }
	@if docker ps --format '{{.Names}}' | grep -qx '$(DB_CONTAINER)'; then \
		docker stop $(DB_CONTAINER) >/dev/null; \
		echo "Stopped $(DB_CONTAINER)"; \
	else \
		echo "Container $(DB_CONTAINER) is not running"; \
	fi

db-migrate:
	@ALEMBIC_DATABASE_URL="$(DATABASE_URL)" $(ALEMBIC) upgrade head

db-downgrade:
	@ALEMBIC_DATABASE_URL="$(DATABASE_URL)" $(ALEMBIC) downgrade -1

db-verify:
	@command -v psql >/dev/null 2>&1 || { echo "psql is required"; exit 1; }
	@psql "$(PSQL_URL)" -v ON_ERROR_STOP=1 -f scripts/db/verify_schema.sql

##@ Code Quality

.PHONY: format
format:
	@echo "Formatting code with black..."
	@black backend/ cli/
	@echo "✓ Code formatted"

.PHONY: lint
lint:
	@echo "Running ruff linter..."
	@ruff check backend/ cli/
	@echo "✓ Linting complete"

.PHONY: type-check
type-check:
	@echo "Running mypy type checker..."
	@mypy backend/app/ cli/zyplat_cli/
	@echo "✓ Type checking complete"

.PHONY: check
check: format lint type-check
	@echo "✓ All code quality checks passed"

.PHONY: fix
fix:
	@echo "Auto-fixing linting issues..."
	@ruff check --fix backend/ cli/
	@black backend/ cli/
	@echo "✓ Auto-fix complete"

##@ Testing

.PHONY: test
test:
	@echo "Running tests..."
	@python -m pytest tests/ -v
	@echo "✓ Tests complete"

.PHONY: test-cov
test-cov:
	@echo "Running tests with coverage..."
	@python -m pytest tests/ -v --cov=backend/app --cov=cli/zyplat_cli --cov-report=html --cov-report=term --cov-fail-under=80
	@echo "✓ Coverage report generated in htmlcov/"
	@echo "✓ Coverage meets minimum threshold of 80%"

.PHONY: test-unit
test-unit:
	@echo "Running unit tests..."
	@python -m pytest tests/unit/ -v
	@echo "✓ Unit tests complete"

.PHONY: test-integration
test-integration:
	@echo "Running integration tests..."
	@python -m pytest tests/integration/ -v
	@echo "✓ Integration tests complete"
