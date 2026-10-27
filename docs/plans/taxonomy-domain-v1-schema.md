# V1 Schema Draft (PostgreSQL)

This document provides a concrete V1 relational schema draft for the taxonomy/domain/company services.

Scope reflected here:

- taxonomy-only versioning
- non-versioned domain definitions
- taxonomy/domain definitions that can be global or company-scoped
- domain dimensions + metrics
- scalar and time-series domain support
- company-owned snapshot tuples with ordinal versioning and default snapshot resolution

## Assumptions

1. UUID primary keys are generated with `gen_random_uuid()`.
2. `company` is a first-class service/table in this repository.
3. One domain instance exists per `(domain_definition_id, company_id)` in V1.
4. Default company snapshot is highest `ord` for `(company_id, period_type, period_value)`.
5. For scalar domains, rows can be stored without a snapshot association.
6. `report_info` is an application-managed array of report records (`report_date` + related domain-instance snapshot ids).

## 1) Extensions

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

## 2) Enums

```sql
CREATE TYPE definition_scope AS ENUM ('GLOBAL', 'COMPANY');

CREATE TYPE company_type AS ENUM ('LENDER', 'BORROWER', 'PARTICIPANT');

CREATE TYPE domain_kind AS ENUM ('TIME_SERIES', 'SCALAR');

CREATE TYPE period_granularity AS ENUM ('YEAR', 'QUARTER', 'MONTH', 'DATE');

CREATE TYPE domain_dimension_data_type AS ENUM (
  'STRING',
  'NUMBER',
  'INTEGER',
  'BOOLEAN',
  'DATE',
  'DATETIME',
  'ENUM',
  'ARRAY_STRING'
);

CREATE TYPE domain_metric_data_type AS ENUM ('NUMBER', 'INTEGER', 'DECIMAL');

CREATE TYPE taxonomy_version_strategy AS ENUM ('LATEST_PUBLISHED', 'PINNED');
```

## 3) Utility trigger for `updated_at`

```sql
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## 4) Company tables

### 4.1 companies

```sql
CREATE TABLE companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL DEFAULT '',
  company_type company_type NOT NULL,
  customer_id TEXT NULL,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  is_test BOOLEAN NOT NULL DEFAULT FALSE,
  naics_code TEXT NULL,
  state TEXT NULL,
  report_info JSONB NOT NULL DEFAULT '[]'::jsonb,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_companies_company_id_not_empty CHECK (length(trim(company_id)) > 0),
  CONSTRAINT ck_companies_name_not_empty CHECK (length(trim(name)) > 0),
  CONSTRAINT ck_companies_report_info_array CHECK (jsonb_typeof(report_info) = 'array'),
  CONSTRAINT ck_companies_metadata_object CHECK (jsonb_typeof(metadata) = 'object')
);

CREATE INDEX ix_companies_customer_id ON companies(customer_id);
CREATE INDEX ix_companies_is_enabled ON companies(is_enabled);
CREATE INDEX ix_companies_is_test ON companies(is_test);
CREATE INDEX ix_companies_naics_code ON companies(naics_code);
CREATE INDEX ix_companies_state ON companies(state);
CREATE INDEX ix_companies_company_type ON companies(company_type);
```

`report_info` payload shape (validated in service layer) should follow:

```json
[
  {
    "report_date": "2026-09",
    "domain_instance_snapshot_ids": [
      "uuid-1",
      "uuid-2"
    ]
  }
]
```

```sql
CREATE TRIGGER trg_companies_updated_at
BEFORE UPDATE ON companies
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
```

### 4.2 company_snapshots

```sql
CREATE TABLE company_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  period_type period_granularity NOT NULL,
  period_value TEXT NOT NULL,
  ord INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_company_snapshot_tuple
    UNIQUE (company_id, period_type, period_value, ord),
  CONSTRAINT ck_company_snapshot_ord_positive CHECK (ord > 0),
  CONSTRAINT ck_company_snapshot_period_format CHECK (
    (period_type = 'YEAR'    AND period_value ~ '^[0-9]{4}$') OR
    (period_type = 'QUARTER' AND period_value ~ '^[0-9]{4}Q[1-4]$') OR
    (period_type = 'MONTH'   AND period_value ~ '^[0-9]{4}-(0[1-9]|1[0-2])$') OR
    (period_type = 'DATE'    AND period_value ~ '^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[0-1])$')
  )
);

CREATE INDEX ix_company_snapshot_default_lookup
  ON company_snapshots (company_id, period_type, period_value, ord DESC);
```

```sql
CREATE TRIGGER trg_company_snapshots_updated_at
BEFORE UPDATE ON company_snapshots
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
```

Optional materialized default pointer table:

```sql
CREATE TABLE company_snapshot_heads (
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  period_type period_granularity NOT NULL,
  period_value TEXT NOT NULL,
  snapshot_id UUID NOT NULL REFERENCES company_snapshots(id) ON DELETE CASCADE,
  PRIMARY KEY (company_id, period_type, period_value)
);
```

## 5) Taxonomy tables

### 5.1 taxonomy_definitions

```sql
CREATE TABLE taxonomy_definitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  taxonomy_id TEXT NOT NULL,
  version TEXT NOT NULL,
  scope_type definition_scope NOT NULL,
  owner_company_id UUID NULL REFERENCES companies(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  is_hierarchical BOOLEAN NOT NULL DEFAULT FALSE,
  allowed_classifications TEXT[] NOT NULL DEFAULT '{}',
  is_published BOOLEAN NOT NULL DEFAULT FALSE,
  published_at TIMESTAMPTZ NULL,
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_taxonomy_definitions_scope_taxonomy_version
    UNIQUE (scope_type, owner_company_id, taxonomy_id, version),
  CONSTRAINT ck_taxonomy_scope_owner
    CHECK (
      (scope_type = 'GLOBAL' AND owner_company_id IS NULL)
      OR
      (scope_type = 'COMPANY' AND owner_company_id IS NOT NULL)
    ),
  CONSTRAINT ck_taxonomy_published_fields
    CHECK ((is_published = FALSE AND published_at IS NULL) OR (is_published = TRUE))
);

CREATE UNIQUE INDEX uq_taxonomy_default_per_scope
  ON taxonomy_definitions (scope_type, owner_company_id, taxonomy_id)
  WHERE is_default = TRUE;

CREATE INDEX ix_taxonomy_lookup
  ON taxonomy_definitions (taxonomy_id, scope_type, owner_company_id, is_published, is_default, updated_at DESC);
```

```sql
CREATE TRIGGER trg_taxonomy_definitions_updated_at
BEFORE UPDATE ON taxonomy_definitions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
```

### 5.2 taxonomy_entities

```sql
CREATE TABLE taxonomy_entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  taxonomy_definition_id UUID NOT NULL REFERENCES taxonomy_definitions(id) ON DELETE CASCADE,
  entity_id TEXT NOT NULL,
  value TEXT NOT NULL,
  display_name TEXT NOT NULL,
  description TEXT NOT NULL,
  parent_entity_id UUID NULL REFERENCES taxonomy_entities(id) ON DELETE RESTRICT,
  explicit_classifications TEXT[] NOT NULL DEFAULT '{}',
  is_base_entity BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_taxonomy_entities_definition_entity UNIQUE (taxonomy_definition_id, entity_id),
  CONSTRAINT ck_taxonomy_entities_entity_id_not_empty CHECK (length(trim(entity_id)) > 0)
);

CREATE INDEX ix_taxonomy_entities_definition
  ON taxonomy_entities (taxonomy_definition_id);

CREATE INDEX ix_taxonomy_entities_parent
  ON taxonomy_entities (taxonomy_definition_id, parent_entity_id);
```

```sql
CREATE TRIGGER trg_taxonomy_entities_updated_at
BEFORE UPDATE ON taxonomy_entities
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
```

Optional hardening (recommended in V1.1 if not in V1):

- Trigger to ensure `parent_entity_id` belongs to the same `taxonomy_definition_id`.
- Trigger to reject cycles.
- Trigger to enforce exactly one root when `is_hierarchical = TRUE`.

## 6) Domain definition tables (non-versioned)

### 6.1 domain_definitions

```sql
CREATE TABLE domain_definitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_id TEXT NOT NULL,
  scope_type definition_scope NOT NULL,
  owner_company_id UUID NULL REFERENCES companies(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  kind domain_kind NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_domain_definitions_scope_domain
    UNIQUE (scope_type, owner_company_id, domain_id),
  CONSTRAINT ck_domain_scope_owner
    CHECK (
      (scope_type = 'GLOBAL' AND owner_company_id IS NULL)
      OR
      (scope_type = 'COMPANY' AND owner_company_id IS NOT NULL)
    ),
  CONSTRAINT ck_domain_id_not_empty CHECK (length(trim(domain_id)) > 0)
);

CREATE INDEX ix_domain_definitions_kind ON domain_definitions(kind);
```

```sql
CREATE TRIGGER trg_domain_definitions_updated_at
BEFORE UPDATE ON domain_definitions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
```

### 6.2 domain_dimensions

```sql
CREATE TABLE domain_dimensions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_definition_id UUID NOT NULL REFERENCES domain_definitions(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  display_name TEXT NOT NULL,
  data_type domain_dimension_data_type NOT NULL,
  required BOOLEAN NOT NULL DEFAULT FALSE,
  is_filter BOOLEAN NOT NULL DEFAULT FALSE,
  ordinal INTEGER NOT NULL,
  taxonomy_id TEXT NULL,
  taxonomy_version_strategy taxonomy_version_strategy NULL,
  taxonomy_version TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_domain_dimensions_name UNIQUE (domain_definition_id, name),
  CONSTRAINT uq_domain_dimensions_ordinal UNIQUE (domain_definition_id, ordinal),
  CONSTRAINT ck_domain_dimension_name_not_empty CHECK (length(trim(name)) > 0),
  CONSTRAINT ck_domain_dimensions_taxonomy_binding
    CHECK (
      (taxonomy_id IS NULL AND taxonomy_version_strategy IS NULL AND taxonomy_version IS NULL)
      OR
      (
        taxonomy_id IS NOT NULL
        AND taxonomy_version_strategy IS NOT NULL
        AND (
          (taxonomy_version_strategy = 'PINNED' AND taxonomy_version IS NOT NULL)
          OR
          (taxonomy_version_strategy = 'LATEST_PUBLISHED' AND taxonomy_version IS NULL)
        )
      )
    )
);

CREATE INDEX ix_domain_dimensions_taxonomy_lookup
  ON domain_dimensions (taxonomy_id, taxonomy_version_strategy, taxonomy_version);
```

```sql
CREATE TRIGGER trg_domain_dimensions_updated_at
BEFORE UPDATE ON domain_dimensions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
```

### 6.3 domain_metrics

```sql
CREATE TABLE domain_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_definition_id UUID NOT NULL REFERENCES domain_definitions(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  display_name TEXT NOT NULL,
  data_type domain_metric_data_type NOT NULL,
  ordinal INTEGER NOT NULL,
  is_point_in_time BOOLEAN NOT NULL DEFAULT FALSE,
  is_end_value BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_domain_metrics_name UNIQUE (domain_definition_id, name),
  CONSTRAINT uq_domain_metrics_ordinal UNIQUE (domain_definition_id, ordinal),
  CONSTRAINT ck_domain_metric_name_not_empty CHECK (length(trim(name)) > 0)
);
```

```sql
CREATE TRIGGER trg_domain_metrics_updated_at
BEFORE UPDATE ON domain_metrics
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
```

## 7) Domain instances and data

### 7.1 domain_instances

```sql
CREATE TABLE domain_instances (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_definition_id UUID NOT NULL REFERENCES domain_definitions(id) ON DELETE RESTRICT,
  company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  classification_scope TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_domain_instance_domain_company UNIQUE (domain_definition_id, company_id)
);

CREATE INDEX ix_domain_instances_company ON domain_instances(company_id);
```

```sql
CREATE TRIGGER trg_domain_instances_updated_at
BEFORE UPDATE ON domain_instances
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
```

### 7.2 domain_instance_snapshots (association to company snapshot tuples)

```sql
CREATE TABLE domain_instance_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_instance_id UUID NOT NULL REFERENCES domain_instances(id) ON DELETE CASCADE,
  company_snapshot_id UUID NOT NULL REFERENCES company_snapshots(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_domain_instance_company_snapshot
    UNIQUE (domain_instance_id, company_snapshot_id)
);

CREATE INDEX ix_domain_instance_snapshots_company_snapshot
  ON domain_instance_snapshots(company_snapshot_id);
```

```sql
CREATE TRIGGER trg_domain_instance_snapshots_updated_at
BEFORE UPDATE ON domain_instance_snapshots
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
```

Note: default snapshot head materialization is handled at company level via `company_snapshot_heads`.

### 7.3 domain_instance_entities

```sql
CREATE TABLE domain_instance_entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_instance_id UUID NOT NULL REFERENCES domain_instances(id) ON DELETE CASCADE,
  domain_instance_snapshot_id UUID NULL REFERENCES domain_instance_snapshots(id) ON DELETE CASCADE,
  data JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_domain_instance_entities_data_object
    CHECK (jsonb_typeof(data) = 'object')
);

CREATE INDEX ix_domain_instance_entities_instance
  ON domain_instance_entities(domain_instance_id);

CREATE INDEX ix_domain_instance_entities_snapshot
  ON domain_instance_entities(domain_instance_snapshot_id);

CREATE INDEX ix_domain_instance_entities_data_gin
  ON domain_instance_entities
  USING GIN (data);
```

```sql
CREATE TRIGGER trg_domain_instance_entities_updated_at
BEFORE UPDATE ON domain_instance_entities
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
```

## 8) Service-level validations still required

DB constraints enforce structure, but these remain in application logic:

1. Taxonomy hierarchy cycle detection.
2. Exactly one root entity for hierarchical taxonomies.
3. `explicit_classifications` subset validation against taxonomy `allowed_classifications`.
4. Parent-child classification inheritance semantics.
5. Domain dimension taxonomy binding must resolve to a published taxonomy version in visible scope.
6. Global + company-scoped visibility filtering for taxonomy/domain definitions.
7. Domain instance `classification_scope` must be valid for bound taxonomies.
8. Domain-instance entity taxonomy dimension values must satisfy scope + base rules.
9. Scalar-domain rule: permit null `domain_instance_snapshot_id`; time-series-domain rule: require non-null snapshot association.
10. Domain snapshot association must match company identity:
    - `domain_instances.company_id` must equal `company_snapshots.company_id` via `domain_instance_snapshots`.
11. `companies.report_info` items must contain valid `report_date` and only domain-instance snapshot ids that belong to the same company.

## 9) Query for default company snapshot (highest ord)

Without `company_snapshot_heads`:

```sql
SELECT s.*
FROM company_snapshots s
WHERE s.company_id = :company_id
  AND s.period_type = :period_type
  AND s.period_value = :period_value
ORDER BY s.ord DESC
LIMIT 1;
```

