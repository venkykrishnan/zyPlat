# Taxonomy and Domain Service Plan (Draft v1)

## 1) Goal and scope

Build a REST service that supports:

1. CRUD for taxonomy definitions
2. CRUD for taxonomy entities
3. CRUD for domain definitions
4. CRUD for domain instances
5. CRUD for domain-instance entities (time-series and scalar)

This plan follows `docs/Goals/TaxonomyAndDomain.md` and incorporates clarifications:

- All taxonomies and domains are configurable.
- Taxonomy versioning exists; domain versioning does not.
- Domain schemas include dimensions and metrics.
- Domains support both time-series and scalar use.
- Time-series domain instances support period granularity: year, quarter, month, date.
- Time-series snapshots are versioned by ordinal (`ord`) per `(domain, company, period)` key.

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

## 3.1 Taxonomy definition

`taxonomy_definitions`

- `id` (UUID, PK)
- `taxonomy_id` (string, logical id; e.g. `accountType`)
- `version` (string or int; start with string to match imported inputs)
- `description` (string)
- `is_hierarchical` (bool)
- `allowed_classifications` (text array, default empty)
- `is_published` (bool)
- `published_at` (timestamp nullable)
- `is_default` (bool)
- `created_at`, `updated_at`

Constraints:

- unique: `(taxonomy_id, version)`
- one default per taxonomy_id (partial unique index on `is_default = true`)

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
- `domain_id` (string, unique logical id; e.g. `GL`, `Inventory`)
- `description` (string)
- `kind` (enum: `TIME_SERIES` | `SCALAR`)
- `created_at`, `updated_at`

Notes:

- Domain schemas include dimensions and metrics.
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
- `company_id` (string; borrower id)
- `classification_scope` (text array, default empty)
- `created_at`, `updated_at`

Rules:

- `classification_scope` values must be in the taxonomy classifications referenced by domain taxonomy-backed dimensions.
- Base entities (no classification) are always valid and do not require scope membership.

## 3.7 Time-series snapshots (for TIME_SERIES domains)

`domain_instance_snapshots`

- `id` (UUID, PK; snapshot id)
- `domain_instance_id` (FK)
- `period_type` (enum: YEAR | QUARTER | MONTH | DATE)
- `period_value` (string canonicalized: `YYYY`, `YYYYQn`, `YYYY-MM`, `YYYY-MM-DD`)
- `ord` (int; monotonically increasing per `(domain_instance_id, period_type, period_value)`)
- `is_default` (bool; optional materialization)
- `created_at`, `updated_at`

Constraints:

- unique: `(domain_instance_id, period_type, period_value, ord)`
- if materializing `is_default`, enforce one default per `(domain_instance_id, period_type, period_value)`

Default rule:

- Default snapshot is highest `ord` for `(domain_instance_id, period_type, period_value)`.
- Optionally maintain with trigger/transactional service update for quick reads.

## 3.8 Domain-instance entities

`domain_instance_entities`

- `id` (UUID, PK)
- `domain_instance_id` (FK)
- `snapshot_id` (nullable FK -> domain_instance_snapshots.id; required for TIME_SERIES, null for SCALAR if desired)
- `data` (jsonb)
- `created_at`, `updated_at`

Rules:

- For TIME_SERIES domain, `snapshot_id` is required.
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

## 5) API design (v1)

Base path: `/v1`

## 5.1 Taxonomy definitions

- `POST /taxonomies`
- `GET /taxonomies`
- `GET /taxonomies/{taxonomyId}/versions/{version}`
- `PUT /taxonomies/{taxonomyId}/versions/{version}`
- `DELETE /taxonomies/{taxonomyId}/versions/{version}`
- `POST /taxonomies/{taxonomyId}/versions/{version}/publish`
- `POST /taxonomies/{taxonomyId}/versions/{version}/unpublish`
- `POST /taxonomies/{taxonomyId}/versions/{version}/set-default`

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
  - request includes: `periodType`, `periodValue`, `rows`
  - server computes next `ord`
- `GET /domain-instances/{instanceId}/snapshots`
  - optional filter: `periodType`, `periodValue`
- `GET /domain-instances/{instanceId}/snapshots/default`
  - requires `periodType`, `periodValue`; returns highest-ord snapshot
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
5. Introduce domain instance and snapshot records where ciqFE uses period-based imported snapshots.

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
- Implement taxonomy binding validation in dimensions.

## Phase 3: domain instances and scalar rows

- Implement domain instance CRUD.
- Implement scalar instance entity CRUD and validation logic.

## Phase 4: time-series snapshots

- Implement period model and snapshot ord rules.
- Implement default snapshot resolution endpoints.
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
- Scope checks for taxonomy-backed dimensions.
- Period parser/normalizer by granularity.
- Snapshot ordinal assignment and default selection.

## Integration tests

- Full CRUD flows for taxonomy/domain/domain-instance.
- Hierarchical taxonomy + classified entity insertion and update.
- Time-series snapshot creation across multiple ords for same company/period.
- Default snapshot retrieval for highest ord.
- Validation failures for unpublished/pinned taxonomy version mismatch.

## 10) Open design decisions to confirm before implementation

1. Should taxonomy `version` be semantic string (e.g. `1.0`) or integer?
2. Should a domain dimension allow `LATEST_PUBLISHED` only, or both strategies from day one?
3. For scalar domains, do we require a synthetic snapshot or allow direct unsnapshotted rows?
4. Should default snapshot always be highest ord, or manually overrideable?
5. Do we need soft delete and audit trail fields in v1?

## 11) Deliverables

1. Source code for service + migrations
2. OpenAPI spec generated from implementation
3. Automated test suite (unit + integration)
4. Seed/import examples (including ciqFE-adapter examples)
5. Runbook for local setup and CI usage

## 12) Linked schema draft

- V1 SQL schema draft: `docs/plans/taxonomy-domain-v1-schema.md`

