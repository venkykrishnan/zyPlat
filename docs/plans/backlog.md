# Backlog

Status values: `TODO`, `IN PROGRESS`, `DONE`.

| Item | Status |
|---|---|
| Add API routes, CRUD, and schemas for company snapshots and snapshot heads (ordinal `ord` logic, default resolution) | TODO |
| Add API routes, CRUD, and schemas for domain dimensions and metrics | TODO |
| Add API routes, CRUD, and schemas for domain instances and snapshots, including endpoints that call `InstanceDataService` to write and read TIME_SERIES frames | TODO |
| Add CLI commands for domain instances | TODO |
| Add central error handler (`api/error_handlers.py`) mapping the typed exceptions in `core/exceptions.py` to a stable response shape with request id (exceptions exist; handler does not) | TODO |
| Add structured JSON logging with `request_id` middleware | TODO |
| Move business rules out of routers into a service layer (routers currently raise `HTTPException`; `services/instance_data.py` is the first service) | TODO |
| Align code layout with `AGENTS.md` module structure (`modules/<name>/...`) | TODO |
| Align CI Python version (3.11, and mypy `python_version`) with the 3.12 baseline in `AGENTS.md` | TODO |
| Add `Code Quality Checks` and `Run Tests` to the required status checks on `main` once the ruff and mypy cleanup lands (`main` was unprotected; it now requires only `Verify Alembic Migrations`, with up-to-date branches, no required reviews, admins not enforced) | TODO |
| Review unmerged remote branches (`cursor/*`) and merge or delete each | TODO |
| Resolve remaining model/migration drift (`alembic check` reported about 35 operations before recent fixes): `domain_instance_entities` (`data` column in migration and schema doc vs `dimensions`/`metrics` in model), `TEXT` vs `VARCHAR` columns, lookup index names (`ix_domain_lookup` vs `ix_domain_definitions_kind`), `ix_domain_instance_snapshots_instance` missing from migrations, and every table not yet covered by `TestModelsMatchMigrations`. Then make `alembic/env.py` fail loudly instead of swallowing model import errors (`target_metadata=None`) | TODO |
| Fix `Makefile` default `DATABASE_URL` (`postgresql+psycopg://`, needs psycopg 3) to match the psycopg2 dependency | TODO |
| Check `Dockerfile`: `COPY alembic.ini ./` (no such file at the repo root; it is `backend/alembic.ini`), and test the new `INSTANCE_DATA_DIR` setup | TODO |
| Fix the 30 mypy errors in 6 files (mostly legacy `Column` typing in models and CRUD) so the "Code Quality Checks" CI job can pass; it fails on mypy today, which also skips the test job | TODO |
| Run `scripts/db/verify_schema.sql` in CI | TODO |
| Trim tutorial-style examples in `docs/conventions/*.md` now that tooling enforces most of them | TODO |
| Resolve duplicate-case files in `input/domains/` (`GeneralLedger.json` vs `generalLedger.json`, `LoanPayment.json` vs `loanPayment.json`); on macOS they show as modified in git | TODO |
| Implement taxonomy version resolution (published, default, pinned) so `InstanceDataService` can derive `allowed_values` itself instead of taking them from the caller | TODO |
| Add S3 implementation of `InstanceDataStore` (local backend loses data on Render or ECS without a persistent volume) | TODO |
| Add orphan-file cleanup for files whose pointer never committed (see `TODO` in `services/instance_data.py`) | TODO |
| Decide retention for superseded snapshots (older `ord` values) | TODO |
| Answer remaining open questions in `instance-data-storage.md` (volumes, API vs direct SQL consumers, Render hosting) | TODO |
| Evaluate DuckDB for cross-snapshot queries over Parquet | TODO |
| Python FastAPI implementation of company, taxonomy, and domain definitions on `main` | DONE |
| CI quality gates (black, ruff, mypy) and 80% coverage gate on PRs to `main` | DONE |
| Decide instance data storage approach (Postgres metadata plus immutable Parquet per snapshot, local filesystem for v1) | DONE |
| Define `InstanceDataStore` protocol with local-filesystem implementation (write-once, atomic, checksummed) | DONE |
| Generate Arrow schema from domain dimension and metric definitions | DONE |
| Add Alembic migration `20261031_0002` for storage pointer columns on `domain_instance_snapshots` | DONE |
| Add write-time DataFrame validation against the domain definition and taxonomy values | DONE |
| Add `InstanceDataService` (write, read, cleanup on failed commit) with unit, integration, and migration tests | DONE |
| Update plan, schema docs, and Alembic plan for the storage design | DONE |
| Fix company `metadata`: it was never saved on create or update (CRUD wrote it to a plain Python attribute) and reads failed response validation; the public name is `metadata`, mapped to the `metadata_` column | DONE |
| Fix NULL-owner uniqueness: duplicate global taxonomy versions, global domains, and several default versions of one global taxonomy were allowed in the models, and the default rule was also broken in the migration (new migration `20261031_0003`) | DONE |
| Add a separate CI `migrations` job that does not depend on `code-quality`; confirmed passing on the PR (Postgres 15, Python 3.11) | DONE |
| Delete the obsolete `db/` Alembic copy after the CI `migrations` job passed | DONE |
| Clear all ruff errors in `backend/` and `cli/` (136 to 0), including `published_at` being stored hours off when the database timezone is not UTC (`utcnow()` replaced with `now(UTC)`) | DONE |
| Protect `main`: require the `Verify Alembic Migrations` status check | DONE |
| Make `backend/alembic` the single working Alembic setup (fixed `script_location` and enum creation; CI migration step previously could not succeed) | DONE |
