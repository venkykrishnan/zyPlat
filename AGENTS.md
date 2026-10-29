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

### Test Coverage Requirements

**Minimum Coverage Gates:**
- **80% overall code coverage** required to merge PRs
- Coverage enforcement is automated in CI/CD pipeline
- Tests must pass before deployment to any environment

### Test Pyramid Structure

Follow the test pyramid for every feature:

1. **Unit tests** (70% of tests) - Business rules, validators, model constraints
2. **Integration tests** (25% of tests) - API + DB interactions, end-to-end workflows
3. **Migration tests** (5% of tests) - Upgrade/downgrade where practical

### Minimum Required Test Areas

Critical test areas for this project:

- **Taxonomy**:
  - Hierarchy validation and parent-child relationships
  - Classification inheritance
  - Version resolution (published/default/pinned)
  - Global vs company scope constraints
  - Unique constraints (scope + owner + taxonomy_id + version)
  
- **Domain**:
  - Domain kinds (TIME_SERIES vs SCALAR)
  - Scope validation (GLOBAL vs COMPANY)
  - Dimension taxonomy binding (LATEST_PUBLISHED vs PINNED)
  - Metric data type validation
  - Domain instance validation against dimensions
  
- **Company**:
  - Company types (LENDER, BORROWER, PARTICIPANT)
  - Snapshot period format validation (YEAR, QUARTER, MONTH, DATE)
  - Ordinal versioning (ord > 0, uniqueness)
  - Snapshot head composite key behavior

### Test Design Principles

**1. Test Isolation**
- Each test must be independent and idempotent
- Use fixtures for database session and test client
- Tests should not depend on execution order
- Clean up test data in teardown (handled by transaction rollback)

**2. Test Organization**
```
tests/
├── conftest.py              # Shared fixtures (db_session, client)
├── unit/                    # Unit tests (fast, no external dependencies)
│   ├── test_domain_models.py
│   ├── test_taxonomy_models.py
│   └── test_company_models.py
└── integration/             # Integration tests (with DB, API)
    ├── test_domain_api.py
    ├── test_taxonomy_api.py
    └── test_company_api.py
```

**3. What to Unit Test**
- Model creation with valid data
- Model validation and constraint enforcement
- Business logic in service/CRUD layers
- Edge cases and boundary conditions
- Negative tests (invalid data should raise exceptions)
- Database constraints (unique, check, foreign key)

**4. What to Integration Test**
- Full CRUD API endpoint workflows
- Request validation (Pydantic schemas)
- Response format and status codes
- Error handling (404, 400, 500 responses)
- Pagination and filtering
- Cross-entity relationships
- End-to-end user workflows

**5. Test Naming Convention**
```python
def test_<action>_<expected_result>(self, fixtures):
    """Docstring explaining what is being tested and why."""
```

Examples:
- `test_create_global_taxonomy()` - Happy path
- `test_global_taxonomy_cannot_have_owner()` - Negative test
- `test_unique_constraint_scope_taxonomy_version()` - Constraint validation

**6. Test Structure (Arrange-Act-Assert)**
```python
def test_example(self, db_session):
    # Arrange - Set up test data
    company = Company(company_id="TEST", name="Test", ...)
    db_session.add(company)
    db_session.flush()
    
    # Act - Perform the action
    result = crud.get_company(db_session, company.id)
    
    # Assert - Verify the outcome
    assert result is not None
    assert result.company_id == "TEST"
```

**7. Fixture Best Practices**
- Use `scope="session"` for expensive setup (DB engine creation)
- Use `scope="function"` for test-specific data (DB session, test client)
- Transaction-based cleanup: wrap each test in a transaction that rolls back
- Avoid complex fixture chains (max 2-3 levels deep)

**8. Assertion Best Practices**
- Test one concept per test function
- Use specific assertions (`assert x == y`, not `assert x`)
- Test both positive and negative cases
- Verify all important attributes, not just one
- Use `pytest.raises()` for exception testing

**9. Database Testing**
```python
# Good: Test actual constraints
with pytest.raises(Exception):  # IntegrityError, ConstraintViolation, etc.
    db_session.commit()

# Good: Test relationships
assert len(taxonomy.entities) == 3
assert child.parent.entity_id == "PARENT"
```

**10. API Testing**
```python
# Test successful creation
response = client.post("/api/v1/companies", json=payload)
assert response.status_code == status.HTTP_201_CREATED
assert response.json()["company_id"] == "TEST001"
assert "id" in response.json()

# Test validation errors
response = client.post("/api/v1/companies", json=invalid_payload)
assert response.status_code == status.HTTP_400_BAD_REQUEST

# Test 404 errors
response = client.get(f"/api/v1/companies/{fake_uuid}")
assert response.status_code == status.HTTP_404_NOT_FOUND
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run specific test file
pytest tests/unit/test_domain_models.py -v

# Run specific test function
pytest tests/unit/test_domain_models.py::TestDomainDefinition::test_create_global_time_series_domain -v

# Run tests matching pattern
pytest -k "taxonomy" -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v
```

### Coverage Analysis

```bash
# Generate HTML coverage report
pytest --cov=backend/app --cov-report=html
open htmlcov/index.html

# Check coverage threshold
pytest --cov=backend/app --cov-fail-under=80
```

### When to Write Tests

**Before writing code (TDD approach):**
1. Write failing test for new feature
2. Implement minimal code to pass test
3. Refactor while keeping tests green

**After writing code (traditional approach):**
1. Implement feature
2. Write comprehensive unit tests
3. Write integration tests
4. Verify coverage meets threshold

**Always test when:**
- Adding new models or API endpoints
- Modifying business logic or validation rules
- Fixing bugs (write test that reproduces bug first)
- Refactoring existing code

### CI/CD Test Integration

Tests run automatically on:
- Every push to any branch
- Every pull request
- Before deployment to any environment

**Deployment is blocked if:**
- Any test fails
- Coverage drops below 80%
- Code quality checks fail (black, ruff, mypy)

## Code evolution and maintainability

### Principles for Modifying Existing Code

**Goal:** Evolve code without adding unnecessary complexity.

#### 1. The Boy Scout Rule
**Always leave code better than you found it.**

When modifying existing code:
- Fix obvious bugs or code smells you encounter
- Improve variable/function names if unclear
- Add missing docstrings or type hints
- Extract complex logic into well-named functions
- Remove dead code or unused imports

**Example:**
```python
# Before modifying to add new feature
def process_data(data):
    x = data['amount']
    if x > 0:
        y = x * 1.1
        return y
    return x

# After (improved while adding feature)
def process_data(data: dict) -> float:
    """Process transaction amount with markup if positive.
    
    Args:
        data: Transaction dictionary containing 'amount' key
        
    Returns:
        Processed amount (positive amounts get 10% markup)
    """
    amount = data['amount']
    if amount > 0:
        return apply_markup(amount, rate=0.10)
    return amount

def apply_markup(amount: float, rate: float) -> float:
    """Apply percentage markup to amount."""
    return amount * (1 + rate)
```

#### 2. Refactor Before Extending

**When to refactor:**
- Before adding a new feature to messy code
- When you need to understand code to fix a bug
- When the same pattern appears 3+ times (Rule of Three)
- When a function/class has grown too large (>50 lines for functions, >200 for classes)

**When NOT to refactor:**
- Right before a deadline (schedule it for later)
- Without test coverage (write tests first)
- Just because code is "not your style"

**Refactoring workflow:**
1. Ensure tests exist and pass
2. Make small, incremental changes
3. Run tests after each change
4. Commit working refactors separately from feature changes

#### 3. Managing Complexity

**Complexity Red Flags:**
- Function with >3 levels of nesting
- Function with >4 parameters
- Class with >10 public methods
- Cyclomatic complexity >10
- File >500 lines

**Strategies to Reduce Complexity:**

**A. Extract Functions**
```python
# Complex: nested conditionals and logic
def create_company_snapshot(company_id, period_type, period_value, data):
    if period_type == "YEAR":
        if not re.match(r'^\d{4}$', period_value):
            raise ValueError("Invalid year format")
    elif period_type == "QUARTER":
        if not re.match(r'^\d{4}Q[1-4]$', period_value):
            raise ValueError("Invalid quarter format")
    # ... more validation ...
    
    # ... business logic ...
    snapshot = CompanySnapshot(...)
    return snapshot

# Better: extracted validation
def create_company_snapshot(company_id, period_type, period_value, data):
    validate_period_format(period_type, period_value)
    snapshot_data = prepare_snapshot_data(data)
    return build_snapshot(company_id, period_type, period_value, snapshot_data)

def validate_period_format(period_type: PeriodGranularity, period_value: str):
    """Validate period value matches expected format for type."""
    validators = {
        PeriodGranularity.YEAR: r'^\d{4}$',
        PeriodGranularity.QUARTER: r'^\d{4}Q[1-4]$',
        PeriodGranularity.MONTH: r'^\d{4}-(0[1-9]|1[0-2])$',
    }
    pattern = validators.get(period_type)
    if pattern and not re.match(pattern, period_value):
        raise ValueError(f"Invalid {period_type.value} format: {period_value}")
```

**B. Use Guard Clauses (Early Returns)**
```python
# Nested conditionals (hard to follow)
def process_taxonomy(taxonomy_id, company_id):
    if taxonomy_id:
        taxonomy = get_taxonomy(taxonomy_id)
        if taxonomy:
            if taxonomy.is_published or company_id == taxonomy.owner_company_id:
                return taxonomy
            else:
                raise PermissionError("Not authorized")
        else:
            raise NotFoundError("Taxonomy not found")
    else:
        raise ValueError("taxonomy_id required")

# Guard clauses (easier to follow)
def process_taxonomy(taxonomy_id: str, company_id: UUID) -> TaxonomyDefinition:
    """Get taxonomy if user has access."""
    if not taxonomy_id:
        raise ValueError("taxonomy_id required")
    
    taxonomy = get_taxonomy(taxonomy_id)
    if not taxonomy:
        raise NotFoundError(f"Taxonomy {taxonomy_id} not found")
    
    if taxonomy.is_published:
        return taxonomy
    
    if company_id == taxonomy.owner_company_id:
        return taxonomy
    
    raise PermissionError("Not authorized to access unpublished taxonomy")
```

**C. Use Data Classes or Pydantic Models for Parameter Groups**
```python
# Too many parameters (hard to remember order)
def create_domain(domain_id, description, kind, scope_type, owner_company_id, 
                  is_published, version, metadata):
    pass

# Better: grouped in a model
from pydantic import BaseModel

class DomainCreateParams(BaseModel):
    domain_id: str
    description: str
    kind: DomainKind
    scope_type: DefinitionScope
    owner_company_id: UUID | None = None
    is_published: bool = False
    version: str = "1.0.0"
    metadata: dict = {}

def create_domain(params: DomainCreateParams) -> Domain:
    """Create domain from validated parameters."""
    pass
```

#### 4. Technical Debt Management

**Acceptable Technical Debt:**
- Quick fixes with TODO comments and tickets
- Temporary workarounds for external API issues
- Performance optimizations deferred until metrics show need

**Unacceptable Technical Debt:**
- Skipping tests "temporarily"
- Ignoring type checking errors
- Commented-out code (delete it, it's in git history)
- Copy-pasted code without refactoring

**Marking Technical Debt:**
```python
# Good: actionable TODO with context
# TODO(venky, 2026-10-29): Refactor to use async when SQLAlchemy 2.1 released
# See: https://github.com/sqlalchemy/sqlalchemy/issues/1234

# Bad: vague TODO
# TODO: fix this later
```

#### 5. When to Rewrite vs Refactor

**Refactor when:**
- Tests exist and pass
- Core logic is sound, just messy
- Small to medium scope (<1000 lines)
- Gradual improvement is possible

**Consider rewriting when:**
- No tests exist and adding them is harder than rewriting
- Fundamental design flaws require complete rework
- Technology stack has changed
- Security vulnerabilities in approach

**Never rewrite:**
- Working code you "just don't like"
- Code written in a different style
- Code you don't fully understand (understand first, then decide)

## Code reuse strategies

### The DRY Principle (Don't Repeat Yourself)

**Core Rule:** Every piece of knowledge should have a single, authoritative representation.

#### 1. When to Extract Shared Code

**Rule of Three:** If code appears 3+ times, consider extracting it.

**Good candidates for extraction:**
- Business logic used in multiple places
- Validation rules
- Data transformations
- Common query patterns
- Utility functions

**Bad candidates for extraction:**
- Code that looks similar but represents different concepts
- Code that changes for different reasons
- UI-specific formatting (keep near UI code)

**Example - Extract Common Validation:**
```python
# Before: Duplicated validation
class CompanyCreate(BaseModel):
    company_id: str
    
    @validator('company_id')
    def validate_company_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("company_id cannot be empty")
        if len(v) > 50:
            raise ValueError("company_id too long")
        return v.strip().upper()

class DomainCreate(BaseModel):
    domain_id: str
    
    @validator('domain_id')
    def validate_domain_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("domain_id cannot be empty")
        if len(v) > 50:
            raise ValueError("domain_id too long")
        return v.strip().upper()

# After: Shared validation function
def validate_id_field(value: str, field_name: str, max_length: int = 50) -> str:
    """Validate and normalize ID field.
    
    Args:
        value: Raw ID value
        field_name: Name of field (for error messages)
        max_length: Maximum allowed length
        
    Returns:
        Normalized ID (trimmed, uppercase)
        
    Raises:
        ValueError: If validation fails
    """
    if not value or len(value.strip()) == 0:
        raise ValueError(f"{field_name} cannot be empty")
    
    normalized = value.strip().upper()
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} too long (max {max_length})")
    
    return normalized

class CompanyCreate(BaseModel):
    company_id: str
    
    @validator('company_id')
    def validate_company_id(cls, v):
        return validate_id_field(v, "company_id")

class DomainCreate(BaseModel):
    domain_id: str
    
    @validator('domain_id')
    def validate_domain_id(cls, v):
        return validate_id_field(v, "domain_id")
```

#### 2. Creating Reusable Utilities

**Location for shared utilities:**
```
app/
  utils/
    validators.py      # Common validation functions
    formatters.py      # Data formatting utilities
    transformers.py    # Data transformation logic
    date_utils.py      # Date/time helpers
    text_utils.py      # String manipulation
```

**Characteristics of good utility functions:**
- Pure functions (no side effects)
- Well-documented with examples
- Type-annotated
- Well-tested
- Single purpose

**Example:**
```python
# app/utils/validators.py
from typing import Pattern
import re

def validate_period_format(
    period_type: str, 
    period_value: str, 
    patterns: dict[str, Pattern]
) -> bool:
    """Validate period value matches format for type.
    
    Args:
        period_type: Type of period (YEAR, QUARTER, etc.)
        period_value: Value to validate
        patterns: Dict mapping types to compiled regex patterns
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If format is invalid
        
    Example:
        >>> patterns = {"YEAR": re.compile(r'^\d{4}$')}
        >>> validate_period_format("YEAR", "2024", patterns)
        True
        >>> validate_period_format("YEAR", "24", patterns)
        ValueError: Invalid YEAR format: 24
    """
    pattern = patterns.get(period_type)
    if not pattern:
        raise ValueError(f"Unknown period type: {period_type}")
    
    if not pattern.match(period_value):
        raise ValueError(f"Invalid {period_type} format: {period_value}")
    
    return True
```

#### 3. Sharing CRUD Patterns

**Create base CRUD operations for common patterns:**

```python
# app/crud/base.py
from typing import TypeVar, Generic, Type
from sqlalchemy.orm import Session
from uuid import UUID

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base class for CRUD operations.
    
    Reduces boilerplate by providing common operations.
    Inherit and override for custom behavior.
    """
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    def get(self, db: Session, id: UUID) -> ModelType | None:
        """Get single record by ID."""
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        """Get multiple records with pagination."""
        return db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Create new record."""
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self, db: Session, *, db_obj: ModelType, obj_in: UpdateSchemaType
    ) -> ModelType:
        """Update existing record."""
        obj_data = obj_in.model_dump(exclude_unset=True)
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, id: UUID) -> bool:
        """Delete record by ID."""
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False

# Usage in specific CRUD modules
class CRUDCompany(CRUDBase[Company, CompanyCreate, CompanyUpdate]):
    """Company-specific CRUD with custom methods."""
    
    def get_by_company_id(self, db: Session, company_id: str) -> Company | None:
        """Get company by company_id (not UUID)."""
        return db.query(Company).filter(Company.company_id == company_id).first()
    
    def get_by_type(
        self, db: Session, company_type: CompanyType
    ) -> list[Company]:
        """Get all companies of specific type."""
        return db.query(Company).filter(Company.company_type == company_type).all()

company = CRUDCompany(Company)
```

#### 4. Using Mixins for Shared Model Behavior

```python
# app/models/mixins.py
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

class TimestampMixin:
    """Add created_at and updated_at to models."""
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(), 
        onupdate=func.now()
    )

class SoftDeleteMixin:
    """Add soft delete capability."""
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    def soft_delete(self):
        """Mark as deleted without removing from DB."""
        self.deleted_at = func.now()

# Usage
from app.models.mixins import TimestampMixin

class Company(Base, TimestampMixin):
    __tablename__ = "companies"
    # created_at and updated_at are automatically included
    id = Column(UUID, primary_key=True)
    name = Column(String, nullable=False)
```

#### 5. Avoiding Premature Abstraction

**Warning Signs of Premature Abstraction:**
- Creating "framework" before you have 2+ use cases
- Adding parameters "just in case we need it later"
- Building plugin systems before you have plugins
- Creating abstractions for code that rarely changes

**Rule:** Wait until you have 2-3 concrete examples before abstracting.

**Example of Premature Abstraction:**
```python
# Too early: building flexible system before knowing requirements
class GenericProcessor:
    def __init__(self, strategy, validator, transformer, serializer):
        self.strategy = strategy
        self.validator = validator
        self.transformer = transformer
        self.serializer = serializer
    
    def process(self, data, options):
        # Overly flexible, hard to understand
        pass

# Better: start simple, refactor when patterns emerge
def process_company_data(company_data: dict) -> Company:
    """Process company data into model."""
    validate_company_data(company_data)
    normalized = normalize_company_data(company_data)
    return Company(**normalized)
```

#### 6. When to Duplicate Code

**It's OK to duplicate when:**
- The code represents different business concepts
- The code is likely to change independently
- Coupling would create unwanted dependencies
- You're still exploring the design space

**Example where duplication is acceptable:**
```python
# company/formatters.py
def format_company_name(name: str) -> str:
    """Format company name for display."""
    return name.strip().title()

# user/formatters.py  
def format_user_name(name: str) -> str:
    """Format user name for display."""
    return name.strip().title()

# Even though implementation is identical, these represent
# different concepts that may diverge (e.g., company names
# might need to preserve abbreviations: "IBM Corp")
```

#### 7. Sharing Configuration

**Use config files for environment-specific values:**
```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Centralized configuration."""
    PROJECT_NAME: str = "zyPlat"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 100
    MAX_PAGE_SIZE: int = 1000
    
    # Validation rules
    MAX_COMPANY_ID_LENGTH: int = 50
    MAX_TAXONOMY_ID_LENGTH: int = 50
    
    class Config:
        env_file = ".env"

settings = Settings()

# Use throughout application
from app.core.config import settings

def get_companies(skip: int = 0, limit: int = settings.DEFAULT_PAGE_SIZE):
    pass
```

#### 8. Documentation for Reusable Code

**All reusable utilities MUST have:**
- Clear docstring with purpose
- Type hints for all parameters and return
- Examples in docstring
- Unit tests demonstrating usage

```python
def calculate_ordinal(
    db: Session, 
    company_id: UUID, 
    period_type: PeriodGranularity, 
    period_value: str
) -> int:
    """Calculate next ordinal for company snapshot.
    
    Finds the highest existing ordinal for the given company/period
    combination and returns the next value.
    
    Args:
        db: Database session
        company_id: Company UUID
        period_type: Type of period (YEAR, QUARTER, etc.)
        period_value: Period value (e.g., "2024", "2024Q1")
        
    Returns:
        Next available ordinal (starts at 1)
        
    Example:
        >>> # First snapshot for 2024
        >>> calculate_ordinal(db, company_id, PeriodGranularity.YEAR, "2024")
        1
        >>> # Second snapshot for 2024
        >>> calculate_ordinal(db, company_id, PeriodGranularity.YEAR, "2024")
        2
    """
    max_ord = (
        db.query(func.max(CompanySnapshot.ord))
        .filter(
            CompanySnapshot.company_id == company_id,
            CompanySnapshot.period_type == period_type,
            CompanySnapshot.period_value == period_value,
        )
        .scalar()
    )
    return (max_ord or 0) + 1
```

### Summary: Code Reuse Checklist

Before creating shared code, ask:
- [ ] Does this appear in 3+ places? (Rule of Three)
- [ ] Do all uses represent the same concept?
- [ ] Will the uses change together or independently?
- [ ] Is the abstraction simple and obvious?
- [ ] Can I write good tests and documentation?
- [ ] Is now the right time, or should I wait for more examples?

If yes to all, create shared code. If no, prefer duplication for now.

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

