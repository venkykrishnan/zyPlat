.PHONY: help db-up db-down db-migrate db-downgrade db-verify

DB_CONTAINER ?= zyplat-postgres
DB_PORT ?= 5432
DB_USER ?= postgres
DB_PASSWORD ?= postgres
DB_NAME ?= zyplat
DB_IMAGE ?= postgres:16

DATABASE_URL ?= postgresql+psycopg://$(DB_USER):$(DB_PASSWORD)@localhost:$(DB_PORT)/$(DB_NAME)
PSQL_URL ?= postgresql://$(DB_USER):$(DB_PASSWORD)@localhost:$(DB_PORT)/$(DB_NAME)
ALEMBIC ?= alembic -c db/alembic.ini

help:
	@echo "Available targets:"
	@echo "  make db-up         # Start local Postgres container (or start existing one)"
	@echo "  make db-down       # Stop local Postgres container"
	@echo "  make db-migrate    # Run Alembic upgrade head"
	@echo "  make db-downgrade  # Run Alembic downgrade -1"
	@echo "  make db-verify     # Run schema verification SQL checks"
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
