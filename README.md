# Zyplat taxonomy and domain service

REST service for configurable taxonomies and domains. The design, including how this maps to ciqFE, is in [docs/plans/taxonomy-domain-service.md](docs/plans/taxonomy-domain-service.md). The goal is [docs/Goals/TaxonomyAndDomain.md](docs/Goals/TaxonomyAndDomain.md).

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn zyplat.main:app --reload
```

OpenAPI is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). The default database is SQLite file `zyplat.db` in the working directory.

For PostgreSQL, install the extra and set the URL:

```bash
.venv/bin/pip install -e ".[dev,postgres]"
export ZYPLAT_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/zyplat
```

Tables are created on startup. Add a migration tool before loading data you need to keep across schema changes.

## Test

```bash
.venv/bin/pytest
```

Tests use an in-memory SQLite database and the same services the HTTP API uses.
