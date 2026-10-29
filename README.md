# zyPlat - Python/FastAPI + PostgreSQL

A platform for managing taxonomies, domains, companies, and domain instances, built on the architecture defined in [PR #2](https://github.com/venkykrishnan/zyPlat/pull/2).

## Architecture

```
CLI (Python/Click) → REST API (FastAPI) → PostgreSQL (with Alembic migrations)
```

**Key Features:**
- **UUID-based** primary keys throughout
- **Sophisticated schema** with company snapshots, ordinal versioning
- **Scoped definitions**: Taxonomies and domains can be GLOBAL or COMPANY-scoped
- **Taxonomy versioning** with published/default flags
- **Domain dimensions & metrics** as separate tables with taxonomy bindings
- **Domain instances** with snapshot associations
- **Company snapshots** with period granularity (YEAR, QUARTER, MONTH, DATE)

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.x
- **Database**: PostgreSQL 15+
- **Migrations**: Alembic
- **CLI**: Python Click with Rich formatting
- **API Documentation**: Auto-generated OpenAPI/Swagger

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or Docker)
- pip

### 2. Start PostgreSQL

```bash
# Using Docker Compose
docker-compose up -d

# This starts PostgreSQL on localhost:5432 with:
# - Database: zyplat
# - User: zyplat
# - Password: zyplat
```

### 3. Set Up Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp ../.env.example .env

# Run migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 4. Set Up CLI

```bash
cd cli

# Install in development mode
pip install -e .

# Verify installation
zyplat --help
```

## API Endpoints

### Companies
- `POST /api/v1/companies` - Create company
- `GET /api/v1/companies` - List companies
- `GET /api/v1/companies/{id}` - Get company
- `PUT /api/v1/companies/{id}` - Update company
- `DELETE /api/v1/companies/{id}` - Delete company

### Taxonomies
- `POST /api/v1/taxonomies/definitions` - Create taxonomy definition
- `GET /api/v1/taxonomies/definitions` - List taxonomy definitions
- `GET /api/v1/taxonomies/definitions/{id}` - Get taxonomy definition
- `PUT /api/v1/taxonomies/definitions/{id}` - Update taxonomy definition
- `DELETE /api/v1/taxonomies/definitions/{id}` - Delete taxonomy definition
- `POST /api/v1/taxonomies/entities` - Create taxonomy entity
- `GET /api/v1/taxonomies/definitions/{id}/entities` - List entities for definition
- `GET /api/v1/taxonomies/entities/{id}` - Get taxonomy entity
- `PUT /api/v1/taxonomies/entities/{id}` - Update taxonomy entity
- `DELETE /api/v1/taxonomies/entities/{id}` - Delete taxonomy entity

### Domains
- `POST /api/v1/domains` - Create domain definition
- `GET /api/v1/domains` - List domain definitions
- `GET /api/v1/domains/{id}` - Get domain definition
- `PUT /api/v1/domains/{id}` - Update domain definition
- `DELETE /api/v1/domains/{id}` - Delete domain definition

## CLI Usage

### Companies

```bash
# Create company from file
zyplat company create --file input/companies/companies.json

# Create company inline
zyplat company create --company-id LEND001 --name "Example Lender" --type LENDER

# List all companies
zyplat company list
```

### Taxonomies

```bash
# Import all taxonomies from input/taxonomies/
zyplat taxonomy create

# Import from specific directory
zyplat taxonomy create --dir /path/to/taxonomies

# Import single file
zyplat taxonomy create --file input/taxonomies/accountType.json

# List all taxonomy definitions
zyplat taxonomy list
```

### Domains

```bash
# Import all domains from input/domains/
zyplat domain create

# Import from specific directory
zyplat domain create --dir /path/to/domains

# Import single file
zyplat domain create --file input/domains/generalLedger.json

# List all domain definitions
zyplat domain list
```

### Global Options

```bash
# Use a different API URL
zyplat --api-url http://production-server:8000/api/v1 company list
```

## Database Schema

The schema is defined in the Alembic migration at `backend/alembic/versions/20261024_0001_initial_company_taxonomy_domain.py`.

### Key Tables

1. **companies** - Company records with type (LENDER, BORROWER, PARTICIPANT)
2. **company_snapshots** - Period snapshots with ordinal versioning
3. **company_snapshot_heads** - Materialized default snapshot pointers
4. **taxonomy_definitions** - Taxonomy metadata with scope and versioning
5. **taxonomy_entities** - Taxonomy entities with hierarchy support
6. **domain_definitions** - Domain metadata with kind (TIME_SERIES, SCALAR)
7. **domain_dimensions** - Domain dimensions with taxonomy bindings
8. **domain_metrics** - Domain metrics
9. **domain_instances** - Company-specific domain instances
10. **domain_instance_snapshots** - Snapshot associations
11. **domain_instance_entities** - Actual data rows with dimensions and metrics

### Enums

- **definition_scope**: GLOBAL, COMPANY
- **company_type**: LENDER, BORROWER, PARTICIPANT
- **domain_kind**: TIME_SERIES, SCALAR
- **period_granularity**: YEAR, QUARTER, MONTH, DATE
- **domain_dimension_data_type**: STRING, NUMBER, INTEGER, BOOLEAN, DATE, DATETIME, ENUM, ARRAY_STRING
- **domain_metric_data_type**: NUMBER, INTEGER, DECIMAL
- **taxonomy_version_strategy**: LATEST_PUBLISHED, PINNED

## Input Data

The `input/` folder contains sample data:

### Taxonomies
- `input/taxonomies/accountType.json` - Hierarchical account type taxonomy
- `input/taxonomies/loanType.json` - Loan type taxonomy
- `input/taxonomies/industry.json` - Industry taxonomy

### Domains
- `input/domains/generalLedger.json` - General ledger domain (time-series)
- `input/domains/loanPayment.json` - Loan payment domain (time-series)

### Companies
- `input/companies/companies.json` - Sample companies (lenders and borrowers)

### Domain Instances
- `input/domain-instances/BORR001_GL.json` - General ledger data for borrower 1
- `input/domain-instances/BORR001_LoanPayment.json` - Loan payment data for borrower 1
- (Similar files for BORR002 and BORR003)

## Development

### Database Management

```bash
# Create a new migration
cd backend
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current migration
alembic current

# Show migration history
alembic history
```

### Running Tests

```bash
# Backend tests (coming soon)
cd backend
pytest

# CLI tests (coming soon)
cd cli
pytest
```

## Development

### Code Quality Standards

This project uses automated code quality tools configured in `pyproject.toml`:

- **black** - Code formatter (line length: 100)
- **ruff** - Fast Python linter
- **mypy** - Static type checker
- **pytest** - Test framework

**Install development dependencies:**

```bash
# Backend
pip install -r backend/requirements-dev.txt

# CLI
pip install -r cli/requirements-dev.txt
```

**Run code quality checks:**

```bash
make format      # Format code with black
make lint        # Run ruff linter
make type-check  # Run mypy type checker
make check       # Run all checks
make fix         # Auto-fix linting issues
```

**Run tests:**

```bash
make test        # Run all tests
make test-cov    # Run with coverage report
```

### Coding Conventions

See `AGENTS.md` for comprehensive Python coding style guidelines including:
- Naming conventions (snake_case, PascalCase)
- Import ordering
- Type hints requirements
- Docstring format (Google-style)
- FastAPI-specific conventions
- SQLAlchemy best practices
- Error handling patterns

## Architecture Documentation

Full architecture and schema documentation is available in:
- `docs/plans/taxonomy-domain-service.plan.md` - Architecture plan
- `docs/plans/taxonomy-domain-v1-schema.md` - Complete schema specification
- `docs/plans/alembic-execution-plan.md` - Database migration plan
- `AGENTS.md` - Coding conventions and style guide

## Project Structure

```
zyPlat/
├── backend/
│   ├── app/
│   │   ├── api/           # API route handlers
│   │   ├── core/          # Config and database setup
│   │   ├── crud/          # Database operations
│   │   ├── models/        # SQLAlchemy models
│   │   └── schemas/       # Pydantic schemas
│   ├── alembic/           # Database migrations
│   └── requirements.txt
├── cli/
│   ├── zyplat_cli/        # CLI implementation
│   ├── setup.py
│   └── requirements.txt
├── input/                 # Sample input data
│   ├── taxonomies/
│   ├── domains/
│   ├── companies/
│   └── domain-instances/
├── docs/                  # Documentation
│   ├── Goals/
│   └── plans/
├── scripts/               # Utility scripts
├── AGENTS.md              # Coding conventions
├── Makefile               # Build automation
└── docker-compose.yml     # PostgreSQL setup
```

## License

[Add your license here]
