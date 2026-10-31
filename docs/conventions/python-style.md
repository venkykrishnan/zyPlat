# Python coding style

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

