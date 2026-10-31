# Code comments

**Core Principle:** Comments should explain WHY, not WHAT. The code itself should explain WHAT.

#### When NOT to Comment

**Never write comments that:**
- State the obvious or narrate the code
- Repeat what the code clearly does
- Explain language features
- Add no information beyond the code itself

**Bad Examples (DON'T DO THIS):**
```python
# Increment counter by 1
counter += 1

# Loop through companies
for company in companies:
    pass

# Get company from database
company = db.query(Company).first()

# Check if taxonomy is published
if taxonomy.is_published:
    pass

# Import the UUID type
from uuid import UUID

# Define the Company class
class Company(Base):
    pass

# Return the result
return result
```

These comments add zero value and make code harder to read. **DELETE THEM.**

#### When TO Comment

**Write comments that explain:**
- **Why** a decision was made (especially non-obvious ones)
- **Context** that isn't clear from code alone
- **Gotchas** or edge cases
- **Workarounds** for bugs or limitations
- **TODOs** with context and owner
- **Business rules** that aren't obvious

**Good Examples (DO THIS):**
```python
# Use ordinal versioning instead of timestamps to handle concurrent updates
# where multiple snapshots might be created in the same second
snapshot = CompanySnapshot(
    company_id=company_id,
    period_value="2024",
    ord=calculate_next_ordinal(db, company_id, period_value)
)

# Pin to SQLAlchemy 2.0.x until async support is stable in 2.1
# See: https://github.com/sqlalchemy/sqlalchemy/issues/1234
dependencies = ["sqlalchemy>=2.0.0,<2.1.0"]

# Taxonomy lookup must check scope_type to prevent company-scoped
# taxonomies from leaking to other companies (security requirement)
if taxonomy.scope_type == DefinitionScope.COMPANY:
    if taxonomy.owner_company_id != current_company_id:
        raise PermissionError("Access denied")

# HACK: Reset connection pool after 1000 queries to work around
# connection leak in psycopg2 2.9.9 (remove when upgrading to 3.x)
if query_count > 1000:
    engine.dispose()

# Business rule: Published taxonomies become immutable to maintain
# referential integrity across domain definitions that depend on them
if taxonomy.is_published:
    raise ValueError("Cannot modify published taxonomy")
```

#### Self-Documenting Code

**Instead of commenting, improve the code:**

```python
# ❌ Bad: Need comment to explain
# Check if company is a lender and is enabled
if c.type == "LENDER" and c.enabled:
    pass

# ✅ Good: Code explains itself
if company.is_active_lender():
    pass

# ❌ Bad: Cryptic variable needs comment
# t is taxonomy
t = get_taxonomy(tid)

# ✅ Good: Clear variable name
taxonomy = get_taxonomy(taxonomy_id)

# ❌ Bad: Magic number needs comment
# 86400 is seconds in a day
if elapsed > 86400:
    pass

# ✅ Good: Named constant
SECONDS_PER_DAY = 86400
if elapsed > SECONDS_PER_DAY:
    pass

# Or even better:
from datetime import timedelta
MAX_AGE = timedelta(days=1)
if age > MAX_AGE:
    pass
```

#### Comment Style Guidelines

**1. Keep Comments Concise**

```python
# ❌ Verbose (37 words)
# We need to validate that the period value provided by the user matches
# the expected format for the given period type because if we don't validate
# it here, invalid data could be stored in the database which would cause
# problems later when we try to query or display the data.

# ✅ Concise (8 words)
# Validate period format to prevent invalid database entries.
```

**2. Use Complete Sentences**

```python
# ❌ Fragments
# check permission
# fix later
# handle edge case

# ✅ Complete sentences
# Check if user has permission to access unpublished taxonomy.
# TODO(venky, 2026-10-29): Refactor to use caching layer.
# Handle case where company has no snapshots yet.
```

**3. Keep Comments Up to Date**

```python
# ❌ Outdated comment (code changed but comment didn't)
# Return all companies
def get_active_lenders(db: Session):
    return db.query(Company).filter(
        Company.company_type == CompanyType.LENDER,
        Company.is_enabled == True
    ).all()

# ✅ Accurate comment
# Return only active lender companies
def get_active_lenders(db: Session):
    return db.query(Company).filter(
        Company.company_type == CompanyType.LENDER,
        Company.is_enabled == True
    ).all()

# ✅✅ Even better: No comment needed (function name is clear)
def get_active_lenders(db: Session):
    return db.query(Company).filter(
        Company.company_type == CompanyType.LENDER,
        Company.is_enabled == True
    ).all()
```

**4. Avoid Redundant Comments in Code Blocks**

```python
# ❌ Every line commented (redundant)
def create_company(db: Session, company_data: CompanyCreate):
    # Create new Company instance
    company = Company(**company_data.model_dump())
    
    # Add company to session
    db.add(company)
    
    # Commit the transaction
    db.commit()
    
    # Refresh to get generated ID
    db.refresh(company)
    
    # Return the company
    return company

# ✅ No comments needed (code is self-explanatory)
def create_company(db: Session, company_data: CompanyCreate):
    company = Company(**company_data.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company
```

#### TODO Comments

**Format:** `TODO(owner, date): description`

```python
# ✅ Good: Actionable with context
# TODO(venky, 2026-10-29): Add caching layer when QPS exceeds 1000
# See ticket: ZYPLAT-123

# TODO(sarah, 2026-11-01): Migrate to async after SQLAlchemy 2.1 release
# Blocked by: https://github.com/sqlalchemy/sqlalchemy/issues/1234

# ❌ Bad: Vague, no owner, no context
# TODO: fix this
# TODO: make this better
# TODO: refactor
```

#### FIXME and HACK Comments

```python
# FIXME(venky, 2026-10-29): Race condition when two requests create
# same company_id simultaneously. Add unique constraint + retry logic.

# HACK: Work around psycopg2 bug by resetting connection pool.
# Remove when upgrading to psycopg3.
# See: https://github.com/psycopg/psycopg2/issues/1234
```

#### Complex Algorithm Comments

**When algorithm is non-obvious, use block comment:**

```python
def calculate_ordinal(db: Session, company_id: UUID, period: str) -> int:
    """Calculate next ordinal for company snapshot.
    
    Ordinal versioning algorithm:
    1. Query existing snapshots for this company+period
    2. Find max ordinal (defaults to 0 if none exist)
    3. Return max + 1
    
    This ensures sequential versioning even with concurrent updates,
    as the database unique constraint will catch duplicates and
    the caller can retry with the next ordinal.
    """
    max_ord = (
        db.query(func.max(CompanySnapshot.ord))
        .filter(
            CompanySnapshot.company_id == company_id,
            CompanySnapshot.period_value == period
        )
        .scalar()
    )
    return (max_ord or 0) + 1
```

#### AI-Generated Code Comment Anti-Patterns

**Common AI mistakes to avoid:**

```python
# ❌ AI Anti-Pattern 1: Obvious narration
# Loop through the list of companies
for company in companies:
    # Check if the company is enabled
    if company.is_enabled:
        # Append the company to the results list
        results.append(company)

# ✅ Better: No comments (code is clear)
for company in companies:
    if company.is_enabled:
        results.append(company)

# ❌ AI Anti-Pattern 2: Redundant function descriptions
def get_company_by_id(db: Session, company_id: UUID) -> Company:
    # This function gets a company by ID from the database
    # It takes a database session and company ID as parameters
    # It returns a Company object or None if not found
    return db.query(Company).filter(Company.id == company_id).first()

# ✅ Better: Use docstring, not inline comments
def get_company_by_id(db: Session, company_id: UUID) -> Company | None:
    """Retrieve company by UUID."""
    return db.query(Company).filter(Company.id == company_id).first()

# ❌ AI Anti-Pattern 3: Explaining code structure
# Define the create_taxonomy_definition function
def create_taxonomy_definition(db: Session, taxonomy: TaxonomyDefinitionCreate):
    # Create a new TaxonomyDefinition instance from the input data
    db_taxonomy = TaxonomyDefinition(**taxonomy.model_dump())
    # Add it to the database session
    db.add(db_taxonomy)
    # Commit the transaction to persist the data
    db.commit()
    # Refresh the instance to get database-generated values
    db.refresh(db_taxonomy)
    # Return the created taxonomy definition
    return db_taxonomy

# ✅ Better: Only comment non-obvious business logic
def create_taxonomy_definition(db: Session, taxonomy: TaxonomyDefinitionCreate):
    """Create new taxonomy definition."""
    db_taxonomy = TaxonomyDefinition(**taxonomy.model_dump())
    db.add(db_taxonomy)
    db.commit()
    db.refresh(db_taxonomy)
    return db_taxonomy
```

#### Commenting Checklist

Before adding a comment, ask:
- [ ] Does the comment explain WHY, not WHAT?
- [ ] Would better naming eliminate the need for this comment?
- [ ] Is this information truly not obvious from the code?
- [ ] Will this comment stay accurate as code evolves?
- [ ] Is this comment concise (ideally one sentence)?

**If NO to any → don't add the comment or improve the code instead.**

#### Summary: Comment Rules

**DO:**
- ✅ Explain WHY decisions were made
- ✅ Document business rules and constraints
- ✅ Mark TODOs with owner and context
- ✅ Warn about gotchas and edge cases
- ✅ Explain workarounds and hacks
- ✅ Keep comments concise and accurate

**DON'T:**
- ❌ Narrate what the code does line by line
- ❌ State the obvious
- ❌ Explain language features
- ❌ Use comments to compensate for bad code
- ❌ Leave outdated comments
- ❌ Add comments AI would generate

**Golden Rule:** If you're about to add a comment explaining what code does, refactor the code to be clearer instead.

