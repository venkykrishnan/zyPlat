# Alembic Execution Plan (V1 Bootstrap)

This plan describes how to execute the migrations in `backend/alembic/versions/`
(`20261024_0001` initial schema, `20261031_0002` instance snapshot storage pointer,
`20261031_0003` one default taxonomy version per scope).

`backend/alembic` is the single Alembic directory. The older `db/alembic` copy was deleted after
the CI `migrations` job passed on the pull request for this branch.

## 1) Objective

Establish a repeatable migration workflow that can:

1. bootstrap Alembic in a new FastAPI/SQLAlchemy project
2. apply the initial V1 schema migration
3. verify schema correctness
4. rollback safely in development

## 2) Preconditions

- Python 3.12
- PostgreSQL 16 accessible
- project virtual environment created
- database user has rights to create extension (`pgcrypto`), enums, tables, indexes, triggers, and functions

## 3) Suggested repository structure for migration runtime

Migrations are committed under `backend/alembic/versions/`. Runtime files:

- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`

Ensure:

- `script_location = %(here)s/alembic` stays set in `backend/alembic.ini`, so Alembic works from
  any working directory (`make db-migrate` runs from the repo root, CI from `backend/`).
- `ALEMBIC_DATABASE_URL` or `DATABASE_URL` is provided for runtime.
- Postgres enum columns in migrations use `postgresql.ENUM(..., create_type=False)` with explicit
  type creation, otherwise `create_table` tries to create the type a second time.

## 4) Bootstrap steps

1. Install migration dependencies:
   - `alembic`
   - `sqlalchemy`
   - `psycopg[binary]` (or async driver if using async engine)
2. Initialize Alembic config files.
3. Wire `env.py` to read DB URL from settings/environment (e.g. `DATABASE_URL`).
4. Ensure target metadata import is configured for future autogenerate use.
5. Keep this initial revision as an explicit handcrafted baseline migration.

## 4.1 Standard developer commands

A `Makefile` now provides common migration workflow commands:

- `make db-up` (start local Postgres container)
- `make db-migrate` (run `upgrade head`)
- `make db-downgrade` (run `downgrade -1`)
- `make db-verify` (run schema checks in `scripts/db/verify_schema.sql`)
- `make db-down` (stop local Postgres container)

## 5) Apply migration (local/dev)

1. Start local DB:
   - `make db-up`
2. Apply migration:
   - `make db-migrate`
3. Validate alembic version table:
   - `SELECT * FROM alembic_version;`
4. Confirm revision id is `20261031_0003` (`alembic current` shows `(head)`).
5. Run schema checks:
   - `make db-verify`

## 6) Verification checklist

After migration, verify:

1. Enums exist:
   - `definition_scope`, `company_type`, `domain_kind`, `period_granularity`, `domain_dimension_data_type`, `domain_metric_data_type`, `taxonomy_version_strategy`
2. Core tables exist:
   - companies, company_snapshots, company_snapshot_heads
   - taxonomy_definitions, taxonomy_entities
   - domain_definitions, domain_dimensions, domain_metrics
   - domain_instances, domain_instance_snapshots, domain_instance_entities
3. `set_updated_at()` function exists.
4. update triggers exist on all tracked mutable tables.
5. unique and check constraints were created.
6. indexes were created (including GIN index on `domain_instance_entities.data`).

## 7) Rollback procedure (dev only)

1. Run:
   - `make db-downgrade`
2. Validate schema objects are removed.
3. Re-run upgrade to confirm migration remains reversible:
   - `make db-migrate`

## 8) CI execution plan

Implemented as the `migrations` job in `.github/workflows/ci.yml`. It has its own Postgres
database, so the schema the test suite builds in `zyplat_test` is untouched, and it does not
depend on the `code-quality` job, so migration problems surface even while lint is failing:

1. Assert exactly one head.
2. Run `upgrade head`, then assert `alembic current` reports `(head)`.
3. Run `downgrade base`, then `upgrade head` again.

`tests/migration/` repeats these checks from both working directories, verifies the enum types
are removed on downgrade, exercises the rules in the migrated schema directly, and compares
nullability, check constraints, and unique constraints and indexes between migrations and the ORM
models for `domain_instance_snapshots`, `taxonomy_definitions`, and `domain_definitions`.

Not yet done: run `scripts/db/verify_schema.sql` in CI; resolve the remaining model/migration
drift reported by `alembic check` (see `backlog.md`).

## 9) Risk controls

1. Keep migration idempotency where possible (`checkfirst` and guarded SQL).
2. Avoid editing historical applied revisions; add forward revisions only.
3. Treat enum changes as explicit follow-up migrations (especially for `company_type` expansion).
4. Keep cross-table ownership checks (e.g., company snapshot ownership) in service validators and integration tests.

## 10) Immediate next actions

1. Run `make db-verify` and capture output in CI logs.
2. Reconcile `alembic check` drift between models and migrations.

