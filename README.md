# zyPlat

A platform for managing taxonomies, domains, companies, and domain instances with **REST API backend** and **CLI client**.

## Architecture

```
Input Files → CLI (HTTP Client) → REST API Server → Business Logic → JSON File Storage
```

- **Backend**: Express REST API with TypeScript
- **CLI**: Commander-based HTTP client
- **Storage**: JSON files in `input/` folder
- **Communication**: HTTP/REST between CLI and server

## Installation

```bash
npm install
npm run build
```

## Running the Server

Start the REST API server:

```bash
npm run server
```

The server runs on `http://localhost:3000` by default.

**Endpoints:**
- Health: `http://localhost:3000/health`
- Taxonomies: `http://localhost:3000/api/taxonomies`
- Domains: `http://localhost:3000/api/domains`
- Companies: `http://localhost:3000/api/companies`
- Instances: `http://localhost:3000/api/instances`

## CLI Usage

The CLI communicates with the REST API server. **Make sure the server is running before using CLI commands.**

### Global Options

All commands support `--api-url` to specify the API server:

```bash
npm run dev <command> --api-url http://localhost:3000/api
```

### Taxonomy Commands

```bash
# List all taxonomies
npm run dev taxonomy list

# Get a specific taxonomy
npm run dev taxonomy get accountType

# Get taxonomy with entities
npm run dev -- taxonomy get accountType --entities

# Import taxonomies from input folder
npm run dev taxonomy import

# Import specific taxonomy file
npm run dev -- taxonomy import --file input/taxonomies/accountType.json

# Create a new taxonomy
npm run dev -- taxonomy create \
  --id myTaxonomy \
  --name "My Taxonomy" \
  --description "A custom taxonomy" \
  --hierarchical \
  --classifications "CIQ,GAAP"

# Update a taxonomy
npm run dev -- taxonomy update accountType --name "Updated Account Type"

# Delete a taxonomy
npm run dev -- taxonomy delete myTaxonomy

# Add an entity to a taxonomy
npm run dev -- taxonomy add-entity accountType \
  --id MyEntity \
  --value "My Entity" \
  --name "My Entity Display" \
  --description "A custom entity" \
  --parent Assets

# Delete an entity from a taxonomy
npm run dev -- taxonomy delete-entity accountType MyEntity
```

### Domain Commands

```bash
# List all domains
npm run dev domain list

# Get a specific domain
npm run dev domain get GL

# Get domain with schema
npm run dev -- domain get GL --schema

# Import domains from input folder
npm run dev domain import

# Import specific domain file
npm run dev -- domain import --file input/domains/generalLedger.json

# Delete a domain
npm run dev -- domain delete GL
```

### Company Commands

```bash
# List all companies
npm run dev company list

# List only lenders
npm run dev -- company list --type lender

# List only borrowers
npm run dev -- company list --type borrower

# Get a specific company
npm run dev -- company get BORR001

# Import companies from input folder
npm run dev company import

# Import from custom file
npm run dev -- company import --file input/companies/companies.json

# Create a new company
npm run dev -- company create \
  --id BORR999 \
  --name "New Borrower" \
  --type borrower \
  --description "A new borrower company" \
  --industry Software

# Update a company
npm run dev -- company update BORR001 --name "Updated Name"

# Delete a company
npm run dev -- company delete BORR999
```

### Domain Instance Commands

```bash
# List all domain instances
npm run dev instance list

# List instances for a specific company
npm run dev -- instance list --company BORR001

# List instances for a specific domain
npm run dev -- instance list --domain GL

# Get a specific instance
npm run dev -- instance get BORR001_GL_001

# Get instance with data
npm run dev -- instance get BORR001_GL_001 --data

# Get instance with limited data rows
npm run dev -- instance get BORR001_GL_001 --data --limit 5

# Import domain instances from input folder
npm run dev instance import

# Import specific instance file
npm run dev -- instance import --file input/domain-instances/BORR001_GL.json

# Delete an instance
npm run dev -- instance delete BORR001_GL_001
```

## Import Workflow

### Initial Data Load

1. **Start the server:**
   ```bash
   npm run server
   ```

2. **Import all data from input folder:**
   ```bash
   npm run dev taxonomy import    # Import all taxonomies
   npm run dev domain import       # Import all domains
   npm run dev company import      # Import all companies
   npm run dev instance import     # Import all domain instances
   ```

### Custom File Import

Import from custom file paths:

```bash
npm run dev -- taxonomy import --file /path/to/custom/taxonomy.json
npm run dev -- domain import --dir /path/to/custom/domains
npm run dev -- company import --file /path/to/custom/companies.json
npm run dev -- instance import --file /path/to/custom/instance.json
```

Default import directories:
- Taxonomies: `input/taxonomies/`
- Domains: `input/domains/`
- Companies: `input/companies/companies.json`
- Instances: `input/domain-instances/`

## REST API Endpoints

### Taxonomies

- `GET /api/taxonomies` - List all taxonomies
- `GET /api/taxonomies/:id` - Get taxonomy by ID
- `POST /api/taxonomies` - Create taxonomy
- `PUT /api/taxonomies/:id` - Update taxonomy
- `DELETE /api/taxonomies/:id` - Delete taxonomy
- `POST /api/taxonomies/:id/entities` - Add entity
- `PUT /api/taxonomies/:taxonomyId/entities/:entityId` - Update entity
- `DELETE /api/taxonomies/:taxonomyId/entities/:entityId` - Delete entity

### Domains

- `GET /api/domains` - List all domains
- `GET /api/domains/:id` - Get domain by ID
- `POST /api/domains` - Create domain
- `PUT /api/domains/:id` - Update domain
- `DELETE /api/domains/:id` - Delete domain

### Companies

- `GET /api/companies?type=lender|borrower` - List companies
- `GET /api/companies/:id` - Get company by ID
- `POST /api/companies` - Create company
- `PUT /api/companies/:id` - Update company
- `DELETE /api/companies/:id` - Delete company

### Domain Instances

- `GET /api/instances?companyId=&domainId=` - List instances
- `GET /api/instances/:id` - Get instance by ID
- `POST /api/instances` - Create instance
- `PUT /api/instances/:id` - Update instance
- `DELETE /api/instances/:id` - Delete instance
- `POST /api/instances/:id/data` - Add data row

## Project Structure

```
zyPlat/
├── input/                      # Input data files
│   ├── taxonomies/            # Taxonomy definitions
│   ├── domains/               # Domain definitions
│   ├── companies/             # Company data
│   └── domain-instances/      # Company-specific domain data
├── src/
│   ├── server/                # REST API server
│   │   ├── index.ts          # Server entry point
│   │   ├── routes/           # API route handlers
│   │   │   ├── taxonomy.ts
│   │   │   ├── domain.ts
│   │   │   ├── company.ts
│   │   │   └── instance.ts
│   │   └── middleware/       # Error handling
│   │       └── errorHandler.ts
│   ├── client/               # HTTP API client
│   │   └── ApiClient.ts
│   ├── commands/             # CLI command implementations
│   │   ├── taxonomy.ts
│   │   ├── domain.ts
│   │   ├── company.ts
│   │   └── instance.ts
│   ├── models/               # TypeScript interfaces
│   │   ├── Taxonomy.ts
│   │   ├── Domain.ts
│   │   ├── Company.ts
│   │   └── DomainInstance.ts
│   ├── services/             # Business logic
│   │   ├── FileService.ts
│   │   ├── TaxonomyService.ts
│   │   ├── DomainService.ts
│   │   ├── CompanyService.ts
│   │   └── DomainInstanceService.ts
│   └── cli.ts                # CLI entry point
├── package.json
└── tsconfig.json
```

## Data Model

### Taxonomies
- Hierarchical or flat classification systems
- Support multiple classifications (CIQ, GAAP, EDGAR, etc.)
- Entities can inherit classifications from parent entities
- Example: `accountType` taxonomy with Balance Sheet and Income Statement hierarchies

### Domains
- Define data schemas with dimensions and metrics
- Can reference taxonomies for dimension values
- Support time-series and non-time-series data
- Example: General Ledger domain with accountType taxonomy reference

### Companies
- Can be lenders or borrowers
- Classified by industry
- Store metadata specific to company type

### Domain Instances
- Company-specific instantiations of domains
- Can specify which classifications are active
- Store actual data records conforming to domain schema
- Example: TechVenture Solutions' General Ledger data

## Sample Data

The `input/` folder contains sample data:

### Taxonomies (3)
- `accountType.json` - Chart of accounts classification (32 entities)
- `loanType.json` - Loan types (6 entities)
- `industry.json` - Industry classifications (7 entities)

### Domains (2)
- `generalLedger.json` - General Ledger domain
- `loanPayment.json` - Loan Payment tracking domain

### Companies (8)
- 3 Lenders: Pinnacle Capital Partners, Sterling Bridge Finance, Meridian Credit Group
- 5 Borrowers: TechVenture Solutions, Cascade Manufacturing, Wellness Medical, Quantum Analytics, Redwood Industrial

### Domain Instances (5)
- Sample GL and LoanPayment data for multiple borrowers

## Development

```bash
# Install dependencies
npm install

# Run server in development mode with auto-reload
npm run server:dev

# Run CLI in development mode
npm run dev <command>

# Build for production
npm run build

# Run built server
npm start server

# Run built CLI
npm start <command>
```

## Error Handling

The API returns proper HTTP status codes:
- `200` - Success
- `201` - Resource created
- `400` - Validation error
- `404` - Resource not found
- `500` - Internal server error

Error responses include:
```json
{
  "error": "Error message",
  "type": "ErrorType"
}
```

## Environment Variables

- `PORT` - Server port (default: 3000)
- `--api-url` - CLI option to specify API URL (default: http://localhost:3000/api)
