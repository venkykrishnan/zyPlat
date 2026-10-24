# AGENTS.md

This document defines implementation conventions for `zyPlat`.

## Scope

- Applies to all contributors (human and agent) working in this repository.
- Covers architecture, code layout, modularity, error handling, logging, and tests.

## Technology baseline (current plan)

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Pydantic
- pytest

If runtime/framework choices change, keep conventions (modularity, error model, logging, tests) unless explicitly updated.

## Service boundaries

V1 service modules:

1. `company` service
2. `taxonomy` service
3. `domain` service
4. `domain-instance` service

### Ownership model

- Taxonomy and domain definitions may be:
  - global (visible to all companies), or
  - company-scoped (owned by one company).
- Domain instances are always company-associated.
- Snapshot associations for `(company, period, ord)` are owned by the company service.

## Code layout

Prefer domain-oriented modules instead of a flat service layer:

```text
app/
  main.py
  api/
    deps.py
    error_handlers.py
    middleware/
  core/
    config.py
    logging.py
    exceptions.py
  db/
    base.py
    session.py
  modules/
    company/
      models.py
      schemas.py
      repository.py
      service.py
      router.py
      validators.py
      exceptions.py
    taxonomy/
      ...
    domain/
      ...
    domain_instance/
      ...
tests/
```

## Layer responsibilities

- `router.py`
  - request/response handling only
  - dependency injection
  - no business logic
- `service.py`
  - business rules
  - orchestration across repositories/modules
  - transaction boundaries
- `repository.py`
  - database I/O only
  - no business rule branching
- `validators.py`
  - reusable validation helpers

## Modularity and class design

- Keep classes focused and small.
- Prefer composition over inheritance.
- Keep cross-module dependencies one-way where possible:
  - `domain_instance` can call `company` and `domain` services
  - `domain` can call `taxonomy` for binding validation
  - avoid circular service dependencies
- Use explicit interfaces/protocols where it improves testability.

## Error/exception handling

Use typed exceptions in service/repository layers. Do not raise HTTP exceptions from deep layers.

Minimum exception taxonomy:

- `NotFoundError`
- `ConflictError`
- `ValidationError`
- `AuthorizationError`
- `InfrastructureError`

Map exceptions in one place (`api/error_handlers.py`) to consistent HTTP responses:

- `NotFoundError` -> 404
- `ConflictError` -> 409
- `ValidationError` -> 422
- `AuthorizationError` -> 401/403
- fallback -> 500

Response shape should be stable and include:

- machine-readable error code
- human-readable message
- request/trace id

## Logging conventions

- Use structured JSON logs.
- Include: `request_id`, `module`, `operation`, and key identifiers (`company_id`, `taxonomy_id`, `domain_id`, `instance_id`, `snapshot_id`) when available.
- Log levels:
  - `INFO`: lifecycle and normal state transitions
  - `WARNING`: recoverable anomalies, validation warnings
  - `ERROR`: failures with stack traces
- Never log secrets or sensitive payload fields.

## Database and migration rules

- All schema changes must use Alembic migrations.
- Never mutate schema ad hoc in runtime code.
- Keep constraints in DB for structural integrity; enforce complex domain rules in services/validators.
- Add indexes deliberately for lookup and default-resolution paths.

## Testing standards

Test pyramid for every feature:

1. Unit tests (business rules and validators)
2. Integration tests (API + DB interactions)
3. Migration tests (upgrade/downgrade where practical)

Minimum required test areas for this project:

- taxonomy hierarchy + classification inheritance
- taxonomy version resolution (published/default/pinned)
- global/company visibility filtering
- domain taxonomy binding validation
- company snapshot `(company, period, ord)` default resolution
- domain instance row validation against scope and taxonomy-backed dimensions

## Naming and terminology

- Use `company` terminology in code and docs (not `borrower`).
- Use `period_type` and `period_value` for time dimensions.
- Use `ord` for ordinal snapshot sequencing.

## Documentation update rule

When changing architecture-critical behavior:

1. update `docs/plans/taxonomy-domain-service.plan.md`
2. update `docs/plans/taxonomy-domain-v1-schema.md`
3. update this `AGENTS.md` if conventions changed

