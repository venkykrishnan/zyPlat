# Testing standards

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
