# Framework conventions (FastAPI, SQLAlchemy, Click)

## FastAPI-specific conventions

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

**Error handling**: Raise typed exceptions below the router; map them to HTTP in one place
(`api/error_handlers.py`, see `AGENTS.md`). Routers do not catch them.
```python
# Bad - HTTPException in service layer
def get_company_service(db: Session, company_id: UUID):
    company = db.query(Company).get(company_id)
    if not company:
        raise HTTPException(status_code=404)  # Wrong layer!

# Good - typed exception in service; the central handler returns the 404 response
def get_company_service(db: Session, company_id: UUID):
    company = db.query(Company).get(company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found")

@router.get("/companies/{company_id}", response_model=CompanyResponse)
def get_company(company_id: UUID, db: Session = Depends(get_db)):
    return get_company_service(db, company_id)
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

