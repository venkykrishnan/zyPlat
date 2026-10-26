# zyPlat

A platform for managing taxonomies, domains, companies, and domain instances.

## Installation

```bash
npm install
npm run build
```

## Usage

The CLI provides commands for managing:
- **Taxonomies**: Hierarchical or flat classification systems
- **Domains**: Data schemas with dimensions and metrics
- **Companies**: Lenders and borrowers
- **Domain Instances**: Company-specific data for domains

### Taxonomy Commands

```bash
# List all taxonomies
npm run dev taxonomy list

# Get a specific taxonomy
npm run dev taxonomy get accountType

# Get a taxonomy with entities
npm run dev taxonomy get accountType --entities

# Create a new taxonomy
npm run dev taxonomy create \
  --id myTaxonomy \
  --name "My Taxonomy" \
  --description "A custom taxonomy" \
  --hierarchical \
  --classifications "CIQ,GAAP"

# Update a taxonomy
npm run dev taxonomy update accountType --name "Updated Account Type"

# Delete a taxonomy
npm run dev taxonomy delete myTaxonomy

# Add an entity to a taxonomy
npm run dev taxonomy add-entity accountType \
  --id MyEntity \
  --value "My Entity" \
  --name "My Entity Display" \
  --description "A custom entity" \
  --parent Assets

# Delete an entity from a taxonomy
npm run dev taxonomy delete-entity accountType MyEntity
```

### Domain Commands

```bash
# List all domains
npm run dev domain list

# Get a specific domain
npm run dev domain get GL

# Get a domain with schema
npm run dev domain get GL --schema

# Delete a domain
npm run dev domain delete GL
```

### Company Commands

```bash
# List all companies
npm run dev company list

# List only lenders
npm run dev company list --type lender

# List only borrowers
npm run dev company list --type borrower

# Get a specific company
npm run dev company get BORR001

# Create a new company
npm run dev company create \
  --id BORR999 \
  --name "New Borrower" \
  --type borrower \
  --description "A new borrower company" \
  --industry Software

# Update a company
npm run dev company update BORR001 --name "Updated Name"

# Delete a company
npm run dev company delete BORR999
```

### Domain Instance Commands

```bash
# List all domain instances
npm run dev instance list

# List instances for a specific company
npm run dev instance list --company BORR001

# List instances for a specific domain
npm run dev instance list --domain GL

# Get a specific instance
npm run dev instance get BORR001_GL_001

# Get an instance with data
npm run dev instance get BORR001_GL_001 --data

# Get an instance with limited data rows
npm run dev instance get BORR001_GL_001 --data --limit 5

# Delete an instance
npm run dev instance delete BORR001_GL_001
```

## Project Structure

```
zyPlat/
├── input/                      # Input data files
│   ├── taxonomies/            # Taxonomy definitions
│   ├── domains/               # Domain definitions
│   ├── companies/             # Company data
│   └── domain-instances/      # Company-specific domain data
├── src/
│   ├── commands/              # CLI command implementations
│   ├── models/                # TypeScript interfaces
│   ├── services/              # Business logic
│   └── cli.ts                 # CLI entry point
├── package.json
└── tsconfig.json
```

## Data Model

### Taxonomies
- Hierarchical or flat classification systems
- Support multiple classifications (e.g., CIQ, GAAP, EDGAR)
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

## Development

```bash
# Install dependencies
npm install

# Run in development mode
npm run dev <command>

# Build for production
npm run build

# Run built version
npm start <command>

# Run tests (when implemented)
npm test

# Lint code (when configured)
npm run lint
```

## Sample Data

The `input/` folder contains sample data:

### Taxonomies
- `accountType.json` - Chart of accounts classification
- `loanType.json` - Loan types (Senior, Mezzanine, Revolver, etc.)
- `industry.json` - Industry classifications

### Domains
- `generalLedger.json` - General Ledger domain
- `loanPayment.json` - Loan Payment tracking domain

### Companies
- 3 Lenders: Pinnacle Capital Partners, Sterling Bridge Finance, Meridian Credit Group
- 5 Borrowers: TechVenture Solutions, Cascade Manufacturing, Wellness Medical, Quantum Analytics, Redwood Industrial

### Domain Instances
- Sample GL and LoanPayment data for multiple borrowers
