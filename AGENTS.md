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

## Python coding style

### Formatting and linting tools

This project uses automated code quality tools configured in `pyproject.toml`:

- **black** - Code formatter (line length: 100)
- **ruff** - Fast Python linter (replaces flake8, isort, pyupgrade)
- **mypy** - Static type checker
- **pytest** - Test framework

Install dev dependencies:

```bash
# Backend
pip install -r backend/requirements-dev.txt

# CLI
pip install -r cli/requirements-dev.txt
```

### Running code quality checks

```bash
# Format code
black backend/ cli/

# Lint code
ruff check backend/ cli/

# Type check
mypy backend/ cli/

# Run all checks
make lint

# Auto-fix issues
ruff check --fix backend/ cli/
```

### Naming conventions

**Variables and functions**: `snake_case`
```python
company_id = "LEND001"
def get_taxonomy_definition(taxonomy_id: str) -> TaxonomyDefinition:
    pass
```

**Classes**: `PascalCase`
```python
class TaxonomyDefinition(Base):
    pass

class CompanyService:
    pass
```

**Constants**: `UPPER_SNAKE_CASE`
```python
MAX_RETRY_ATTEMPTS = 3
DEFAULT_PAGE_SIZE = 100
```

**Private members**: `_leading_underscore`
```python
class Company:
    def __init__(self):
        self._internal_cache = {}
    
    def _validate_internal(self):
        pass
```

**Type variables**: `PascalCase` with suffix
```python
from typing import TypeVar

ModelT = TypeVar("ModelT", bound=Base)
ResponseT = TypeVar("ResponseT")
```

### Import ordering (enforced by ruff)

```python
# 1. Future imports
from __future__ import annotations

# 2. Standard library
import os
from datetime import datetime
from typing import Optional, List
from uuid import UUID

# 3. Third-party
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# 4. Local application
from ..core.database import get_db
from ..models.company import Company
from ..schemas.company import CompanyCreate
```

### Type hints

**Required for:**
- Public function signatures
- Class method signatures
- Function returns (except `None`)

**Optional for:**
- Private functions
- Simple variable assignments (when type is obvious)

```python
# Good - type hints on public functions
def get_company(db: Session, company_id: UUID) -> Optional[Company]:
    return db.query(Company).filter(Company.id == company_id).first()

# Good - return type annotation
def create_company(db: Session, company: CompanyCreate) -> Company:
    db_company = Company(**company.model_dump())
    db.add(db_company)
    db.commit()
    return db_company

# Acceptable - no hints on obvious types
user_name = "John"  # str is obvious
count = 0  # int is obvious
```

### Docstrings

Use **Google-style docstrings** for public functions/classes:

```python
def get_taxonomy_entities(
    db: Session, 
    definition_id: UUID, 
    skip: int = 0, 
    limit: int = 100
) -> List[TaxonomyEntity]:
    """Retrieve taxonomy entities for a given definition.

    Args:
        db: Database session
        definition_id: UUID of the taxonomy definition
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)

    Returns:
        List of TaxonomyEntity objects

    Raises:
        NotFoundError: If taxonomy definition does not exist
    """
    # Implementation
    pass
```

For simple functions, one-line docstrings are acceptable:

```python
def validate_period_format(period_type: str, period_value: str) -> bool:
    """Validate that period_value matches the format for period_type."""
    # Implementation
    pass
```

### FastAPI-specific conventions

**Dependency injection**: Use `Depends()` explicitly
```python
@router.get("/companies/{company_id}")
def get_company(
    company_id: UUID,
    db: Session = Depends(get_db)  # Explicit Depends
) -> CompanyResponse:
    pass
```

**Response models**: Always specify `response_model`
```python
@router.post("/companies", response_model=CompanyResponse, status_code=201)
def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    pass
```

**Error handling**: Raise HTTPException at router level only
```python
# Bad - HTTPException in service layer
def get_company_service(db: Session, company_id: UUID):
    company = db.query(Company).get(company_id)
    if not company:
        raise HTTPException(status_code=404)  # Wrong layer!

# Good - Domain exception in service, HTTP at router
def get_company_service(db: Session, company_id: UUID):
    company = db.query(Company).get(company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found")

@router.get("/companies/{company_id}")
def get_company(company_id: UUID, db: Session = Depends(get_db)):
    try:
        return get_company_service(db, company_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### SQLAlchemy conventions

**Model field naming**: Use `snake_case`, match database columns
```python
class Company(Base):
    __tablename__ = "companies"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    company_id = Column(String, nullable=False)  # Matches DB column
    created_at = Column(DateTime(timezone=True))
```

**Avoid SQLAlchemy reserved names**: Use trailing underscore if needed
```python
# Bad - 'metadata' is reserved
metadata = Column(JSONB)

# Good - use trailing underscore
metadata_ = Column("metadata", JSONB)
```

**Relationships**: Be explicit about cascade behavior
```python
class TaxonomyDefinition(Base):
    entities = relationship(
        "TaxonomyEntity",
        back_populates="definition",
        cascade="all, delete-orphan"  # Explicit cascade
    )
```

### CLI conventions (Click)

**Command naming**: Use kebab-case for commands
```python
@cli.command("list-taxonomies")  # kebab-case
def list_taxonomies():
    pass
```

**Option naming**: Use long form with double dash
```python
@click.option("--api-url", default="http://localhost:8000")
@click.option("--format", type=click.Choice(["json", "table"]))
def command(api_url: str, format: str):
    pass
```

**Output**: Use Rich for formatting
```python
from rich.console import Console
from rich.table import Table

console = Console()
table = Table(title="Companies")
table.add_column("ID")
table.add_column("Name")
console.print(table)
```

### Error messages

**User-facing errors**: Be specific and actionable
```python
# Bad
raise ValueError("Invalid input")

# Good
raise ValidationError(
    f"Period value '{period_value}' does not match format for {period_type}. "
    f"Expected format: YYYY-MM for MONTH type."
)
```

**Log messages**: Include context
```python
# Bad
logger.error("Failed to create company")

# Good
logger.error(
    "Failed to create company",
    extra={
        "company_id": company.company_id,
        "error": str(e),
        "request_id": request_id
    }
)
```

### Line length and formatting

- **Maximum line length**: 100 characters (enforced by black)
- **Strings**: Use double quotes `"` (enforced by black)
- **Trailing commas**: Always use in multi-line structures (enforced by black)

```python
# Good - trailing comma
company = Company(
    company_id="LEND001",
    name="Example Lender",
    company_type=CompanyType.LENDER,  # Trailing comma
)

# Good - line breaking
very_long_function_call_with_many_arguments(
    first_argument=value1,
    second_argument=value2,
    third_argument=value3,
)
```

### Testing conventions

**Test file naming**: `test_*.py` or `*_test.py`
```
tests/
├── test_company_crud.py
├── test_taxonomy_service.py
└── integration/
    └── test_api_endpoints.py
```

**Test function naming**: Descriptive with `test_` prefix
```python
def test_create_company_with_valid_data():
    pass

def test_get_company_raises_not_found_for_invalid_id():
    pass

def test_taxonomy_hierarchy_validates_parent_in_same_definition():
    pass
```

**Fixtures**: Use pytest fixtures for common setup
```python
import pytest

@pytest.fixture
def db_session():
    # Setup
    session = create_test_session()
    yield session
    # Teardown
    session.close()

def test_company_crud(db_session):
    company = create_company(db_session, company_data)
    assert company.id is not None
```

## Naming and terminology

- Use `company` terminology in code and docs (not `borrower`).
- Use `period_type` and `period_value` for time dimensions.
- Use `ord` for ordinal snapshot sequencing.

## Documentation update rule

When changing architecture-critical behavior:

1. update `docs/plans/taxonomy-domain-service.plan.md`
2. update `docs/plans/taxonomy-domain-v1-schema.md`
3. update this `AGENTS.md` if conventions changed

