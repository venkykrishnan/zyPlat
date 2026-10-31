# Taxonomy and Domain Service Plan (Draft v1)

## 1) Goal and scope

Build a REST service that supports:

1. CRUD for taxonomy definitions
2. CRUD for taxonomy entities
3. CRUD for domain definitions
4. CRUD for company definitions and report metadata
5. CRUD for domain instances
6. CRUD for domain-instance entities (time-series and scalar)

This plan follows `docs/Goals/TaxonomyAndDomain.md` and incorporates clarifications:

- All taxonomies and domains are configurable.
- Taxonomy versioning exists; domain versioning does not.
- Domain schemas include dimensions and metrics.
- Domains support both time-series and scalar use.
- Taxonomy and domain definitions can be global or company-scoped.
- Domain instances are strongly associated with a company.
- Time-series domain instances support period granularity: year, quarter, month, date.
- Company service owns snapshot tuple association `(company, period, ord)` and default resolution.
- Terminology in zyPlat uses `company` (not `borrower`).

## 2) Recommended technology choices

## Primary recommendation

- Language: Python 3.12
- Web framework: FastAPI
- Store: PostgreSQL 16
- ORM: SQLAlchemy 2.x
- Migrations: Alembic
- Validation: Pydantic models + service-layer validators
- Testing: pytest + httpx + testcontainers (Postgres)

## Why this choice

- The domain is relationship-heavy and rule-heavy (hierarchy, inheritance, version resolution, snapshot defaulting), which fits relational integrity strongly.
- OpenAPI-first ergonomics are strong and useful for early review.
- Validation and type contracts are explicit and easy to enforce.

## Alternative if team prefers TypeScript

- Fastify (or NestJS) + PostgreSQL + Prisma/Drizzle

This plan still applies with that stack; only framework/ORM syntax changes.

## 3) Core domain model

## 3.0 Company definition

`companies`

- `id` (UUID, PK)
- `company_id` (string logical id, unique)
- `name` (string, unique)
- `description` (string)
- `company_type` (enum: `LENDER` | `BORROWER` | `PARTICIPANT`)
- `customer_id` (optional string for grouping/tenant hierarchy)
- `is_enabled` (bool)
- `is_test` (bool)
- `naics_code` (optional string)
- `state` (optional string)
- `report_info` (jsonb array; each item includes `report_date` and associated domain-instance snapshot ids)
- `metadata` (jsonb for extensibility)
- `created_at`, `updated_at`

## 3.1 Taxonomy definition

`taxonomy_definitions`

- `id` (UUID, PK)
- `taxonomy_id` (string, logical id; e.g. `accountType`)
- `version` (string or int; start with string to match imported inputs)
- `description` (string)
- `is_hierarchical` (bool)
- `allowed_classifications` (text array, default empty)
- `scope_type` (enum: `GLOBAL` | `COMPANY`)
- `owner_company_id` (nullable FK to company, required for `COMPANY` scope)
- `is_published` (bool)
- `published_at` (timestamp nullable)
- `is_default` (bool)
- `created_at`, `updated_at`

Constraints:

- unique per scope: `(taxonomy_id, version)` for GLOBAL, `(owner_company_id, taxonomy_id, version)` for COMPANY
- one default per taxonomy in each scope: `(taxonomy_id)` for GLOBAL, `(owner_company_id, taxonomy_id)` for COMPANY
- implemented as partial unique indexes, one per scope, because global rows have a NULL owner and Postgres treats NULLs as distinct in a plain unique constraint
- if `scope_type = COMPANY`, `owner_company_id` is required

## 3.2 Taxonomy entities

`taxonomy_entities`

- `id` (UUID, PK)
- `taxonomy_definition_id` (FK -> taxonomy_definitions.id)
- `entity_id` (string, stable in definition scope)
- `value` (string)
- `display_name` (string)
- `description` (string)
- `parent_entity_id` (nullable, self-FK within same taxonomy_definition_id)
- `explicit_classifications` (text array, default empty)
- `is_base_entity` (bool, default true)
- `created_at`, `updated_at`

Constraints and rules:

- unique: `(taxonomy_definition_id, entity_id)`
- if `is_hierarchical = true`, exactly one root (`parent_entity_id is null`)
- no cycles in ancestry
- all `explicit_classifications` must be members of `allowed_classifications`

## 3.3 Domain definition (non-versioned)

`domain_definitions`

- `id` (UUID, PK)
- `domain_id` (string logical id; e.g. `GL`, `Inventory`)
- `description` (string)
- `kind` (enum: `TIME_SERIES` | `SCALAR`)
- `scope_type` (enum: `GLOBAL` | `COMPANY`)
- `owner_company_id` (nullable FK to company, required for `COMPANY` scope)
- `created_at`, `updated_at`

Notes:

- Domain schemas include dimensions and metrics.
- uniqueness is by scope: `(domain_id)` for GLOBAL, `(owner_company_id, domain_id)` for COMPANY (partial unique indexes, see taxonomy note on NULL owners)
- No version column on domains per clarified requirement.

## 3.4 Domain dimensions

`domain_dimensions`

- `id` (UUID, PK)
- `domain_definition_id` (FK)
- `name` (string)
- `display_name` (string)
- `data_type` (enum, e.g. STRING, NUMBER, INTEGER, BOOLEAN, DATE, DATETIME, ENUM, ARRAY_STRING)
- `required` (bool)
- `is_filter` (bool)
- `ordinal` (int)
- `taxonomy_id` (nullable string when taxonomy-backed)
- `taxonomy_version_strategy` (nullable enum: `LATEST_PUBLISHED` | `PINNED`)
- `taxonomy_version` (nullable string; required if strategy=PINNED)
- `created_at`, `updated_at`

Constraints:

- unique: `(domain_definition_id, name)`
- taxonomy-backed dimensions require taxonomy reference fields.
- taxonomy-backed dimensions must resolve to published taxonomy version.

## 3.5 Domain metrics

`domain_metrics`

- `id` (UUID, PK)
- `domain_definition_id` (FK)
- `name` (string)
- `display_name` (string)
- `data_type` (enum: NUMBER | INTEGER | DECIMAL)
- `ordinal` (int)
- metadata fields as needed (e.g., `is_point_in_time`, `is_end_value`)
- `created_at`, `updated_at`

Constraints:

- unique: `(domain_definition_id, name)`

## 3.6 Domain instances

`domain_instances`

- `id` (UUID, PK)
- `domain_definition_id` (FK)
- `company_id` (FK to `companies`)
- `classification_scope` (text array, default empty)
- `created_at`, `updated_at`

Rules:

- `classification_scope` values must be in the taxonomy classifications referenced by domain taxonomy-backed dimensions.
- Base entities (no classification) are always valid and do not require scope membership.

## 3.7 Company snapshot tuples (for TIME_SERIES domains)

`company_snapshots`

- `id` (UUID, PK; snapshot id)
- `company_id` (FK)
- `period_type` (enum: YEAR | QUARTER | MONTH | DATE)
- `period_value` (string canonicalized: `YYYY`, `YYYYQn`, `YYYY-MM`, `YYYY-MM-DD`)
- `ord` (int; monotonically increasing per `(company_id, period_type, period_value)`)
- `created_at`, `updated_at`

Constraints:

- unique: `(company_id, period_type, period_value, ord)`

Default rule:

- Default snapshot is highest `ord` for `(company_id, period_type, period_value)`.
- Company service exposes and resolves this default.

## 3.8 Domain snapshot associations

`domain_instance_snapshots`

- `id` (UUID, PK)
- `domain_instance_id` (FK)
- `company_snapshot_id` (FK -> company_snapshots.id, required)
- `storage_uri`, `row_count`, `schema_hash`, `checksum` (nullable; set together when a TIME_SERIES snapshot's file is written)
- `calc_run_id` (nullable; producing calculation run)
- `created_at`, `updated_at`

Constraints:

- unique: `(domain_instance_id, company_snapshot_id)`
- unique: `storage_uri`
- storage pointer columns are all-or-nothing; `row_count >= 0`

TIME_SERIES snapshot rows are stored as one immutable Parquet file per snapshot, not in Postgres.
See `instance-data-storage.md`.

## 3.9 Domain-instance entities

`domain_instance_entities`

- `id` (UUID, PK)
- `domain_instance_id` (FK)
- `domain_instance_snapshot_id` (nullable FK -> domain_instance_snapshots.id; required for TIME_SERIES, null for SCALAR if desired)
- `data` (jsonb)
- `created_at`, `updated_at`

Rules:

- TIME_SERIES domains do not use this table; their rows are stored in Parquet files (see 3.8).
- For SCALAR domain, either:
  - keep one synthetic snapshot per instance, or
  - allow null snapshot and enforce one active row contract.

## 4) Classification and inheritance logic

## 4.1 Effective classification resolution

`effective(entity) = explicit(entity) ∪ effective(parent)` for hierarchical taxonomies.

- Inherited values are computed, not stored.
- For non-hierarchical taxonomy, effective = explicit.

## 4.2 Validation for taxonomy-backed domain dimensions

When writing domain-instance entity data:

1. Resolve taxonomy definition:
   - PINNED -> exact `taxonomy_id + version`
   - LATEST_PUBLISHED -> latest published default resolution
2. Validate entity id exists in that taxonomy definition.
3. Compute entity effective classifications.
4. Permit value if:
   - entity has no effective classification (base), or
   - `intersection(effective_classifications, classification_scope)` is non-empty.

Additionally for time-series rows:

5. `domain_instance_snapshot_id` must resolve to a snapshot whose company snapshot belongs to the same company as the domain instance.

## 5) API design (v1)

Base path: `/v1`

## 5.0 Company definitions and snapshots

- `POST /companies`
- `GET /companies`
- `GET /companies/{companyId}`
- `PUT /companies/{companyId}`
- `DELETE /companies/{companyId}`

`PUT /companies/{companyId}` supports:

- `company_type`
- `report_info`
- core metadata fields (`description`, `customer_id`, `is_enabled`, `is_test`, `naics_code`, `state`, `metadata`)

Company snapshots:

- `POST /companies/{companyId}/snapshots`
  - request includes: `periodType`, `periodValue`
  - server computes next `ord`
- `GET /companies/{companyId}/snapshots`
  - optional filter: `periodType`, `periodValue`
- `GET /companies/{companyId}/snapshots/default`
  - requires `periodType`, `periodValue`; returns highest-ord snapshot
- `GET /companies/{companyId}/snapshots/{snapshotId}`
- `DELETE /companies/{companyId}/snapshots/{snapshotId}`

## 5.1 Taxonomy definitions

- `POST /taxonomies`
- `GET /taxonomies`
- `GET /taxonomies/{taxonomyId}/versions/{version}`
- `PUT /taxonomies/{taxonomyId}/versions/{version}`
- `DELETE /taxonomies/{taxonomyId}/versions/{version}`
- `POST /taxonomies/{taxonomyId}/versions/{version}/publish`
- `POST /taxonomies/{taxonomyId}/versions/{version}/unpublish`
- `POST /taxonomies/{taxonomyId}/versions/{version}/set-default`

Scope filtering behavior:

- global definitions are always returned
- company-scoped definitions are returned only for the requesting company

## 5.2 Taxonomy entities

- `POST /taxonomies/{taxonomyId}/versions/{version}/entities`
- `GET /taxonomies/{taxonomyId}/versions/{version}/entities`
  - query: `parent`, `classification`, `includeEffective=true|false`
- `GET /taxonomies/{taxonomyId}/versions/{version}/entities/{entityId}`
- `PUT /taxonomies/{taxonomyId}/versions/{version}/entities/{entityId}`
- `DELETE /taxonomies/{taxonomyId}/versions/{version}/entities/{entityId}`

## 5.3 Domain definitions

- `POST /domains`
- `GET /domains`
- `GET /domains/{domainId}`
- `PUT /domains/{domainId}`
- `DELETE /domains/{domainId}`

Scope filtering behavior:

- global definitions are always returned
- company-scoped definitions are returned only for the requesting company

Dimensions:

- `POST /domains/{domainId}/dimensions`
- `GET /domains/{domainId}/dimensions`
- `PUT /domains/{domainId}/dimensions/{dimensionName}`
- `DELETE /domains/{domainId}/dimensions/{dimensionName}`

Metrics:

- `POST /domains/{domainId}/metrics`
- `GET /domains/{domainId}/metrics`
- `PUT /domains/{domainId}/metrics/{metricName}`
- `DELETE /domains/{domainId}/metrics/{metricName}`

## 5.4 Domain instances

- `POST /domain-instances`
- `GET /domain-instances`
- `GET /domain-instances/{instanceId}`
- `PUT /domain-instances/{instanceId}`
- `DELETE /domain-instances/{instanceId}`

## 5.5 Time-series snapshots

- `POST /domain-instances/{instanceId}/snapshots`
  - request includes: `companySnapshotId`
  - associates a domain instance with a company snapshot tuple
- `GET /domain-instances/{instanceId}/snapshots`
  - optional filter: `companySnapshotId`, `periodType`, `periodValue`
- `GET /domain-instances/{instanceId}/snapshots/{snapshotId}`
- `DELETE /domain-instances/{instanceId}/snapshots/{snapshotId}`

## 5.6 Domain-instance entities (row-level CRUD)

- `POST /domain-instances/{instanceId}/entities`
- `GET /domain-instances/{instanceId}/entities`
  - optional filters: snapshot, dimension predicates
- `PUT /domain-instances/{instanceId}/entities/{entityRowId}`
- `DELETE /domain-instances/{instanceId}/entities/{entityRowId}`

## 6) Compatibility with ciqFE and data adaptation

The design can support ciqFE-like taxonomy/domain data with adapters:

1. Remove standard/configurable distinction.
2. Map `isSOR` to classification labels (e.g. `["SOR"]`) in import transform.
3. Preserve hierarchy and parent ids.
4. Add taxonomy version strategy for domain taxonomy-bound dimensions.
5. Introduce company snapshots and domain-instance snapshot associations where ciqFE uses period-based imported snapshots.

## 7) Validation and integrity strategy

## DB-level

- Uniqueness and referential integrity constraints.
- Check constraints for enum combinations.
- Optional trigger/function for default snapshot resolution.

## Service-level

- Hierarchy acyclic checks.
- Root count checks for hierarchical taxonomies.
- Classification inheritance evaluation.
- Taxonomy-backed dimension value validation against scope.
- Period canonicalization by granularity.
- Company-level default snapshot resolution by `(company, period, highest ord)`.
- `report_info` payload validation (`report_date` format + domain-instance snapshot ownership by company).

## 8) Implementation phases

## Phase 0: project bootstrap

- Create FastAPI service skeleton, env config, DB connection, migration pipeline.
- Add lints, formatters, CI checks.

## Phase 1: taxonomy definitions and entities

- Implement taxonomy/version/publish/default CRUD.
- Implement taxonomy entity CRUD with hierarchy + classification validation.
- Add tests for inheritance and root/cycle rules.

## Phase 2: domain definitions

- Implement domain, dimensions, metrics CRUD.
- Implement global/company scope filtering and ownership checks.
- Implement taxonomy binding validation in dimensions.

## Phase 3: company service + domain instances

- Implement company CRUD and updates for `company_type` and `report_info`.
- Implement company snapshot tuple service and default resolution.
- Implement domain instance CRUD.
- Implement scalar instance entity CRUD and validation logic.

## Phase 4: domain time-series snapshots

- Implement company snapshot association endpoints on domain instances.
- Implement row CRUD tied to snapshots.

## Phase 5: migration/import utilities

- Add optional import translators for ciqFE-shaped files.
- Add data verification scripts.

## Phase 6: stabilization

- Performance checks on common filters.
- API hardening, error contract consistency.
- Documentation and sample datasets.

## 9) Test plan

## Unit tests

- Classification inheritance (multi-level).
- Hierarchy cycle detection.
- Taxonomy version resolution (pinned vs latest published).
- global/company visibility filtering on taxonomy and domain definitions.
- Scope checks for taxonomy-backed dimensions.
- Period parser/normalizer by granularity.
- Company snapshot ordinal assignment and default selection.
- Domain-instance to company-snapshot association integrity.

## Integration tests

- Full CRUD flows for company/taxonomy/domain/domain-instance.
- Hierarchical taxonomy + classified entity insertion and update.
- Time-series company snapshot creation across multiple ords for same company/period.
- Default company snapshot retrieval for highest ord.
- Validation failures for unpublished/pinned taxonomy version mismatch.

## 10) Open design decisions to confirm before implementation

The following decisions are now confirmed:

1. Taxonomy `version`: **integer**
2. Domain taxonomy strategy: **both `LATEST_PUBLISHED` and `PINNED` in v1**
3. Scalar domain snapshot policy: **nullable snapshot allowed**
4. Default company snapshot behavior: **always highest `ord`**
5. Soft delete and audit trail in v1: **no**

## 11) Deliverables

1. Source code for service + migrations
2. OpenAPI spec generated from implementation
3. Automated test suite (unit + integration)
4. Seed/import examples (including ciqFE-adapter examples)
5. Runbook for local setup and CI usage

## 12) Linked schema draft

- V1 SQL schema draft: `docs/plans/taxonomy-domain-v1-schema.md`
- Alembic execution plan: `docs/plans/alembic-execution-plan.md`

