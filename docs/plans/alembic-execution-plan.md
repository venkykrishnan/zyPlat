# Alembic Execution Plan (V1 Bootstrap)

This plan describes how to execute the draft migration in `db/alembic/versions/20261024_0001_initial_company_taxonomy_domain.py`.

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

The draft migration is already committed under:

- `db/alembic/versions/20261024_0001_initial_company_taxonomy_domain.py`

Alembic runtime templates are now committed as draft scaffolding:

- `db/alembic.ini`
- `db/alembic/env.py`
- `db/alembic/script.py.mako`

If path conventions change later, update these files accordingly.

During implementation bootstrap, ensure:

- `script_location = db/alembic` remains set in `db/alembic.ini`
- environment variables (`ALEMBIC_DATABASE_URL` or `DATABASE_URL`) are provided for runtime

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
4. Confirm revision id is `20261024_0001`.
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

For PR checks:

1. Start ephemeral Postgres container.
2. Run `upgrade head`.
3. Run schema smoke verification SQL script.
4. Run `downgrade -1` then `upgrade head` again.
5. Run integration tests that rely on migrated schema.

## 9) Risk controls

1. Keep migration idempotency where possible (`checkfirst` and guarded SQL).
2. Avoid editing historical applied revisions; add forward revisions only.
3. Treat enum changes as explicit follow-up migrations (especially for `company_type` expansion).
4. Keep cross-table ownership checks (e.g., company snapshot ownership) in service validators and integration tests.

## 10) Immediate next actions

1. Scaffold FastAPI/SQLAlchemy project skeleton.
2. Execute this migration on local Postgres with `make db-up` + `make db-migrate`.
3. Run `make db-verify` and capture output in CI logs.
4. Add migration smoke tests in CI.

