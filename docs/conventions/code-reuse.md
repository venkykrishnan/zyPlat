# Code reuse strategies

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
