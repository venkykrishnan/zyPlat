# Code evolution and maintainability

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
