# Application Service Plan (Draft v1)

Status: **awaiting review**. This plan follows `docs/Goals/Application.md` steps 1–3 and
5–6. Implementation (step 7) starts only after step 4 (your input).

This document reviews the goal, answers the open questions, and proposes schema, APIs, and a
PR split. It does not change runtime code.

## 1) Goal and scope

Add an **application** as a first-class entity: a named, versioned configuration of existing
domains (each input or output) that can be enabled for many companies, plus **bind instances**
that pin a company’s domain-instance snapshots to an application at a snapshot period.

In the same goal, extend **time-series domains** so one dimension is identified as the time-series
field and imported values are validated against a period granularity.

Out of scope for this goal:

- Running calculations that produce output-domain data
- Authn/authz beyond existing company ownership checks
- Changing taxonomy versioning or company core fields
- Migrating the whole backend to the `modules/<name>/` layout (new application code should
  follow that layout; existing company/taxonomy/domain routers stay as they are)

## 2) Technology choices

Stay on the current zyPlat stack. Do not introduce a second language or store.

| Choice | Value |
|---|---|
| Language | Python 3.12 (CI is still 3.11; tracked in `docs/plans/backlog.md`) |
| Web framework | FastAPI |
| Store | PostgreSQL (same database as company, taxonomy, domain) |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Validation | Pydantic request models + service-layer validators |
| Testing | pytest (unit + integration against Postgres) |
| CLI | Click, via `ZyPlatClient` (no backend imports) |

TIME_SERIES instance rows stay in Parquet, referenced from `domain_instance_snapshots`. Bind
instances do not copy that data; they point at snapshot rows.

## 3) Review of the goal

Two time notions stay distinct:

1. **Snapshot period** — already implemented as `company_snapshots` (`period_type`,
   `period_value`, `ord`). This is the as-of / version of a company’s data, not a row in a table.
2. **Time-series field** — a dimension on a `TIME_SERIES` domain. Instance data is tabular with
   one row per combination of dimensions, including that period field. A July 2026 company
   snapshot of General Ledger may contain many period rows (history), not only July.

Loan Payment currently has three `DATETIME` dimensions (`dueDate`, `paidDate`, `period`). The
platform cannot infer which one is the time-series axis, so the domain must mark exactly one.

A **bind instance** is not another domain instance. Domain instances remain one per
`(domain_definition, company)`: NorthCo has one GL instance, one Revolver instance, one BBC
instance. A bind instance is a **cross-domain view** for a company snapshot: which snapshots of
those instances to show together.

Two snapshot alignments:

1. **Tied to company snapshot** (GL, Revolver, Term Loan). One snapshot file per company
   snapshot. July 2026 revolver payments live under `MONTH 2026-07`.
2. **Independent of company snapshot** (BBC). The BBC instance is created and updated by date
   (`DATE 2026-07-05`, `2026-07-15`, `2026-07-26`) without needing a July company snapshot. In
   zyPlat terms those are **snapshots of the same BBC domain instance**, not three domain
   instances.

The company snapshot matters when the user wants a month view: Revolver, Term Loan, and GL for
July 2026, **plus every BBC snapshot whose date falls in July 2026** (all three dates).

```text
Application (BBC / LoanMonitoring v1)
  domains: GL (INPUT, company-tied), Revolver (INPUT, company-tied),
           TermLoan (INPUT, company-tied), BBC (INPUT, independent)

Company snapshot: NorthCo MONTH 2026-07

Bind instance (the July 2026 view)
  GL snapshot          -> company snapshot 2026-07
  Revolver snapshot    -> company snapshot 2026-07
  TermLoan snapshot    -> company snapshot 2026-07
  BBC snapshots        -> DATE 2026-07-05, 2026-07-15, 2026-07-26
                          (contained in 2026-07; not stored under the company snapshot)
```

## 4) Open questions (proposed answers)

### 4.1 API separation: application vs bind instance

Keep them as **distinct route trees**. Use the noun `bind-instance`, not `bind`.

| Resource | Base path |
|---|---|
| Application definition | `/api/v1/applications` |
| Domain config on an application | `/api/v1/applications/{applicationId}/versions/{version}/domains` |
| Company enablement | `/api/v1/applications/{applicationId}/versions/{version}/companies` |
| Bind instances | `/api/v1/applications/{applicationId}/versions/{version}/bind-instances` |

Company enablement is configuration of the application. Bind instances are runtime data and
should not be mixed into `POST /applications`.

Path ids use the logical `application_id` + `version` (same pattern as taxonomies), not the
row UUID, except where list filters need the UUID.

### 4.2 Does application create check existing domains and taxonomies?

**Yes. Creation fails if anything is missing or inconsistent.**

Domains and taxonomies are not created as a side effect of creating an application. The create
payload names each domain and states the schema the application requires. The service then:

1. Resolves each `domain_id` (global, or company-scoped if `owner_company_id` is supplied).
2. Fails if the domain does not exist.
3. Fails if `kind` does not match.
4. Fails if a `TIME_SERIES` domain does not have exactly one time-series dimension, or if that
   dimension’s name / `period_type` does not match the payload.
5. Fails if any required dimension or metric is missing, has the wrong `data_type`, or (when
   taxonomy-backed) does not bind the expected `taxonomy_id` (and pinned version, if given).
6. Extra dimensions or metrics on the live domain are allowed. The application’s expected
   schema is a **required subset**, not a lock on the whole domain.
7. Taxonomy-backed dimensions must resolve to a published taxonomy version using the domain’s
   existing version strategy.

The live domain definition remains the source of truth. The application stores `domain_definition_id`,
role, and a `schema_hash` of the subset it accepted, so later domain edits can be detected. It
does not store a second copy of dimensions and metrics.

### 4.3 Additional design questions

| Question | Proposed answer |
|---|---|
| Is an application versioned like a taxonomy? | `version` is part of identity: unique `(application_id, version)`. No publish/default workflow in this goal. |
| Global vs company-owned applications? | Applications are **global**. Companies are enabled on a version. Domain refs may still point at company-scoped domains when the owner is explicit. |
| Can a domain be both input and output in one application? | No. One row per `(application, domain)` with role `INPUT` or `OUTPUT`. |
| Must every application domain have a company domain instance at bind time? | Company-tied `INPUT` domains need exactly one snapshot for that company snapshot. Independent `INPUT` domains contribute **every** snapshot whose own period is contained in the company snapshot (three BBC dates in July). `OUTPUT` members may be omitted and attached later. |
| Do BBC dates need two files under one company snapshot? | **No.** BBC snapshots are not keyed by company snapshot. Each BBC date is its own snapshot of the one BBC domain instance. See §6.8. |
| Must every row’s time-series value equal the company snapshot period? | No. Snapshot period is as-of; the time-series field is the row period. Validation is format/alignment only. |
| What is `bind_snapshot` stored as? | Not a column on the bind instance. The bind instance is identified by the **company snapshot** (the view). Independent domains carry their own snapshot period (`DATE 2026-07-05`) on `domain_instance_snapshots`. |
| How does a July view pick BBC rows? | Containment: include independent snapshots whose period falls inside the company snapshot period (`2026-07-05` ⊂ `MONTH 2026-07`). |
| CLI in this goal? | Yes, after the REST APIs, as a follow-on PR. |
| New module layout? | New `application` code lives under `backend/app/modules/application/` (router, service, repository, schemas, models, exceptions). It calls existing company and domain layers. Do not migrate old modules in these PRs. |

## 5) Use cases this plan covers

1. CRUD REST API for applications, including validation against company and domain APIs/services.
2. Domain (and instance-import) changes for the time-series field and period-type validation.
3. CRUD REST API for bind instances on distinct routes.
4. Enabling companies on an application version.
5. Unit and integration tests for the rules above.

## 6) Proposed model

### 6.1 Enums

```sql
CREATE TYPE application_domain_role AS ENUM ('INPUT', 'OUTPUT');
```

Reuse `period_granularity` (`YEAR`, `QUARTER`, `MONTH`, `DATE`).

### 6.2 applications

```text
applications
  id UUID PK
  application_id TEXT NOT NULL          -- logical id, e.g. LoanMonitoring
  version TEXT NOT NULL                 -- e.g. 1.0.0
  name TEXT NOT NULL
  description TEXT NOT NULL DEFAULT ''
  created_at, updated_at
  UNIQUE (application_id, version)
  CHECK length(trim(application_id)) > 0
  CHECK length(trim(version)) > 0
  CHECK length(trim(name)) > 0
```

`name` is not globally unique across versions of the same application. Different applications
should still use different `application_id`s.

### 6.3 application_domains

```text
application_domains
  id UUID PK
  application_id UUID NOT NULL FK applications(id) ON DELETE CASCADE
  domain_definition_id UUID NOT NULL FK domain_definitions(id) ON DELETE RESTRICT
  role application_domain_role NOT NULL
  snapshot_alignment ENUM ('COMPANY', 'INDEPENDENT') NOT NULL
  schema_hash VARCHAR(64) NOT NULL      -- hash of the expected subset accepted at write time
  created_at, updated_at
  UNIQUE (application_id, domain_definition_id)
```

Delete of a domain is restricted while an application references it.

BBC is `INDEPENDENT`. GL, Revolver, and Term Loan are `COMPANY`. Independent snapshots are
included in a company-snapshot view when their own period is contained in that snapshot.

While bind instances exist for that application version, the domain set is immutable except
**adding** an `OUTPUT` domain. Removing a domain, changing a role, or changing an `INPUT`
domain is a `ConflictError`.

### 6.4 application_companies

```text
application_companies
  application_id UUID NOT NULL FK applications(id) ON DELETE CASCADE
  company_id UUID NOT NULL FK companies(id) ON DELETE CASCADE
  created_at
  PRIMARY KEY (application_id, company_id)
```

Enabling a company requires the company to exist. It does not create domain instances.

### 6.5 application_bind_instances

```text
application_bind_instances
  id UUID PK
  application_id UUID NOT NULL FK applications(id) ON DELETE RESTRICT
  company_id UUID NOT NULL FK companies(id) ON DELETE CASCADE
  company_snapshot_id UUID NOT NULL FK company_snapshots(id) ON DELETE RESTRICT
  created_at, updated_at
  UNIQUE (application_id, company_id, company_snapshot_id)
```

Constraints (service + DB):

- `(application_id, company_id)` must exist in `application_companies`.
- `company_snapshots.company_id` must equal `company_id`.

There is **no bind period** on this row. One bind instance is the July 2026 view, not one row
per BBC date.

### 6.6 application_bind_instance_members

```text
application_bind_instance_members
  bind_instance_id UUID NOT NULL FK application_bind_instances(id) ON DELETE CASCADE
  domain_definition_id UUID NOT NULL FK domain_definitions(id) ON DELETE RESTRICT
  domain_instance_snapshot_id UUID NOT NULL FK domain_instance_snapshots(id) ON DELETE RESTRICT
  PRIMARY KEY (bind_instance_id, domain_instance_snapshot_id)
  UNIQUE not required on (bind_instance_id, domain_definition_id)
```

A company-tied domain has **one** member. An independent domain may have **many** (three BBC
dates in July).

Rules:

- `domain_definition_id` must be in `application_domains` for that application.
- The snapshot’s domain instance must be that domain for this company.
- If alignment is `COMPANY`, the snapshot’s `company_snapshot_id` must equal the bind instance’s
  company snapshot, and there is exactly one member for that domain (for `INPUT`).
- If alignment is `INDEPENDENT`, the snapshot has no company snapshot; its own period must be
  contained in the bind instance’s company snapshot period. All such snapshots known at bind
  time are members (the July view includes 5, 15, and 26 July).
- `OUTPUT` members may be omitted and attached later.

### 6.7 Domain changes (existing entity)

On `domain_dimensions`:

```text
is_time_series BOOLEAN NOT NULL DEFAULT FALSE
period_type period_granularity NULL
```

Check constraints:

- `is_time_series = FALSE` ⇒ `period_type IS NULL`
- `is_time_series = TRUE` ⇒ `period_type IS NOT NULL` AND `data_type = 'DATETIME'`

Partial unique index: at most one `is_time_series` dimension per `domain_definition_id`.

Service rules (not fully expressible as row constraints, because dimensions are added after the
domain row):

- `kind = TIME_SERIES` ⇒ exactly one time-series dimension before the domain can be used by an
  application or accept instance data.
- `kind = SCALAR` ⇒ zero time-series dimensions.

`dateTimeScope` in fixture JSON maps to `period_type` as:

| Fixture `dateTimeScope` | `period_type` |
|---|---|
| (none / omitted) | not a time-series field |
| `Year` | `YEAR` |
| `Quarter` | `QUARTER` |
| `MonthYear` | `MONTH` |
| `DateMonthYear` | `DATE` |

For Loan Payment, `period` (`MonthYear`) is the time-series field; `dueDate` and `paidDate` stay
ordinary `DATETIME` dimensions.

### 6.8 Domain-instance snapshot changes (existing entity)

Today `company_snapshot_id` is required and uniqueness is `(domain_instance_id, company_snapshot_id)`.
That fits GL and loans. It does not fit BBC, which must be writable with no July company snapshot
and may have several date snapshots in the same month.

```text
domain_instance_snapshots
  ... existing columns ...
  company_snapshot_id UUID NULL FK company_snapshots(id)  -- nullable (was NOT NULL)
  snapshot_period_type period_granularity NULL
  snapshot_period_value TEXT NULL
```

Exactly one alignment per row:

- **Company-tied:** `company_snapshot_id` set; snapshot period columns null. Period comes from
  the company snapshot. Partial unique `(domain_instance_id, company_snapshot_id)` where
  `company_snapshot_id IS NOT NULL` (same as today).
- **Independent:** `company_snapshot_id` null; snapshot period columns both set and regex-valid.
  Partial unique `(domain_instance_id, snapshot_period_type, snapshot_period_value)` where
  `company_snapshot_id IS NULL`. Restatements of the same BBC date can use `ord` on this row
  later if needed; not required for v1.

Which alignment a domain uses is stored on `application_domains.snapshot_alignment` (and should
match how that domain’s snapshots are written). BBC snapshots are independent; GL snapshots are
company-tied.

Parquet keys already use surrogate ids, so the file path does not encode period.

### 6.9 Import validation of the time-series field

When writing a TIME_SERIES frame (`InstanceDataService` / `validate_frame`):

1. The domain must have exactly one `is_time_series` dimension.
2. That column is required.
3. After conversion to UTC, each value must have time `00:00:00` and equal the **start** of its
   period:

| `period_type` | Canonical value |
|---|---|
| `YEAR` | `{year}-01-01T00:00:00Z` |
| `QUARTER` | first day of Q1/Q2/Q3/Q4 at `00:00:00Z` |
| `MONTH` | `{year}-{month}-01T00:00:00Z` |
| `DATE` | `{year}-{month}-{day}T00:00:00Z` |

Non-aligned values fail with `ValidationError` listing the offending values (cap at five, same
pattern as taxonomy validation).

## 7) API design

Base path remains `/api/v1`. New application routes use typed service exceptions, not
`HTTPException` in the router (`AGENTS.md` / FastAPI conventions).

### 7.1 Applications

- `POST /applications`
- `GET /applications` — query: `application_id`
- `GET /applications/{applicationId}/versions/{version}`
- `PUT /applications/{applicationId}/versions/{version}` — `name`, `description` only
- `DELETE /applications/{applicationId}/versions/{version}` — conflict if bind instances exist

Create body (illustrative):

```json
{
  "application_id": "LoanMonitoring",
  "version": "1.0.0",
  "name": "Loan Monitoring",
  "description": "Monitor borrower loans against lender facilities",
  "domains": [
    {
      "domain_id": "GL",
      "role": "INPUT",
      "expected": {
        "kind": "TIME_SERIES",
        "time_series_dimension": "period",
        "period_type": "MONTH",
        "dimensions": [
          {"name": "period", "data_type": "DATETIME"},
          {"name": "account", "data_type": "STRING"}
        ],
        "metrics": [
          {"name": "amount", "data_type": "NUMBER"}
        ]
      }
    }
  ]
}
```

### 7.2 Application domains (optional nested updates)

- `POST /applications/{applicationId}/versions/{version}/domains` — add an `OUTPUT` domain
- `GET /applications/{applicationId}/versions/{version}/domains`
- `DELETE /applications/{applicationId}/versions/{version}/domains/{domainId}` — only if no
  bind instances, or only `OUTPUT` with no members

### 7.3 Company enablement

- `PUT /applications/{applicationId}/versions/{version}/companies/{companyId}` — enable
- `GET /applications/{applicationId}/versions/{version}/companies`
- `DELETE /applications/{applicationId}/versions/{version}/companies/{companyId}` — conflict if
  bind instances exist for that company

### 7.4 Bind instances

- `POST /applications/{applicationId}/versions/{version}/bind-instances`
- `GET /applications/{applicationId}/versions/{version}/bind-instances`
  — query: `company_id`, `period_type`, `period_value`
- `GET .../bind-instances/{bindInstanceId}`
- `PUT .../bind-instances/{bindInstanceId}` — replace optional OUTPUT members only
- `DELETE .../bind-instances/{bindInstanceId}`

Create body (illustrative):

```json
{
  "company_id": "NorthCo",
  "period_type": "MONTH",
  "period_value": "2026-07",
  "members": [
    {"domain_id": "GL", "domain_instance_snapshot_id": "uuid-gl-july"},
    {"domain_id": "Revolver", "domain_instance_snapshot_id": "uuid-rev-july"},
    {"domain_id": "TermLoan", "domain_instance_snapshot_id": "uuid-tl-july"},
    {"domain_id": "BBC", "domain_instance_snapshot_id": "uuid-bbc-0705"},
    {"domain_id": "BBC", "domain_instance_snapshot_id": "uuid-bbc-0715"},
    {"domain_id": "BBC", "domain_instance_snapshot_id": "uuid-bbc-0726"}
  ]
}
```

`company_snapshot_id` may be sent instead of `period_type` / `period_value`. If only period is
sent, resolve the default (highest `ord`) company snapshot. Missing snapshot is `NotFoundError`.

Create may also **resolve members** for independent domains: given the company snapshot period,
attach every independent snapshot whose period is contained in it, so the client does not have
to list the three BBC ids.

### 7.5 Domain API additions needed for the time-series field

Dimension CRUD is still a backlog item. The time-series PR must expose enough surface to set
`is_time_series` and `period_type`:

- Nested dimensions/metrics on `POST /domains`, or
- `POST/PUT /domains/{domainId}/dimensions` including the new fields.

This plan prefers nested create plus dimension PUT, so a TIME_SERIES domain can be created in
one request with its time-series field.

## 8) Validation summary

| Layer | Rules |
|---|---|
| DB | Uniqueness, FKs, period regex, time-series column pairing, at most one time-series dimension |
| Service | Exactly one time-series dimension on TIME_SERIES domains; expected schema subset; taxonomy published; company enabled; company-tied vs independent member rules; independent snapshot period contained in company snapshot; snapshot ownership |
| Import | Time-series column present, UTC midnight, aligned to `period_type` |

Error mapping stays the existing taxonomy: `NotFoundError` 404, `ConflictError` 409,
`ValidationError` 422.

## 9) Tests

Minimum coverage (counts toward the 80% CI gate):

- Application create success; fail on missing domain; fail on kind mismatch; fail on missing
  time-series field; fail on dimension type mismatch; extra domain fields allowed.
- Taxonomy-backed expected dimension fails when taxonomy is missing or unpublished.
- Duplicate `(application_id, version)` is 409.
- Enable unknown company is 404; disable company with bind instances is 409.
- Bind instance without company enablement is 409.
- Bind instance missing a company-tied INPUT snapshot is 422.
- July bind instance accepts three BBC date snapshots and one GL snapshot; a fourth BBC date
  outside July is 422; two GL snapshots for the same month is 422.
- BBC date snapshot can be created with `company_snapshot_id` null.
- Duplicate bind instance for the same `(application, company, company_snapshot)` is 409.
- TIME_SERIES import: aligned month succeeds; `2026-07-15` on a `MONTH` field fails;
  two `is_time_series` dimensions rejected.
- SCALAR domain rejecting a time-series dimension.

## 10) PR split

Small, reviewable PRs. PRs that **modify existing entities** are called out.

| PR | Touches existing entities? | Contents |
|---|---|---|
| **PR 1 — Time-series dimension** | **Yes: `domain_dimensions`, instance-data validation** | Alembic: `is_time_series`, `period_type`, checks, partial unique index. Model + dimension create/update API (or nested domain create). `validate_frame` period alignment. Unit/integration tests. Update `taxonomy-domain-v1-schema.md` §6.2 and `taxonomy-domain-service.plan.md` §3.4. Fixture mapping note for `dateTimeScope`. |
| **PR 2 — Company snapshot API** | **Yes: exposes existing `company_snapshots` / heads** | CRUD + default resolution as already specified in `taxonomy-domain-service.plan.md` §5.0. Prerequisite for bind instances. Tests for `ord` and period regex. This is already on the backlog; do it here because bind instances depend on it. |
| **PR 3 — Application definition** | No (new tables only; reads company/domain) | `applications`, `application_domains`, `application_companies`. Module under `backend/app/modules/application/`. REST CRUD + company enablement + expected-schema validation. Tests. Update `AGENTS.md` V1 service list. |
| **PR 4 — Bind instances** | **Yes: `domain_instance_snapshots.company_snapshot_id` becomes nullable; independent snapshot period columns** | Snapshot migration (nullable FK, partial unique indexes). `application_bind_instances` + members (many snapshots per independent domain). Bind-instance REST and July-view containment. Tests for BBC dates 5/15/26 plus GL/Revolver for `MONTH 2026-07`. Update schema docs §7.2. |
| **PR 5 — CLI + goal close-out** | No | Click commands for applications, enablement, bind instances. Refresh `docs/Goals/Application.md` use cases from the reviewed plan. |

Do not combine PR 1 or PR 4 with the new application tables. Domain and snapshot uniqueness
changes should review independently of application CRUD.

Suggested merge order: 1 → 2 → 3 → 4 → 5. PR 3 can overlap PR 2 in development but should not
merge before snapshot default resolution exists if we want bind-instance tests on `main`.

## 11) Documentation updates (when implementing)

Per `AGENTS.md`, each architecture PR updates:

1. `docs/plans/taxonomy-domain-service.plan.md` — time-series field, nullable company snapshot on instance snapshots
2. `docs/plans/taxonomy-domain-v1-schema.md` — new columns/tables
3. `AGENTS.md` — add `application` to V1 services (PR 3)
4. `docs/Goals/Application.md` — record decided answers (after this review)
5. `docs/plans/backlog.md` — mark snapshot API done when PR 2 lands

## 12) What this plan needs from you

Please confirm or correct:

1. Route split and the name `bind-instance` (§4.1).
2. Application create validates a **required subset** of the live domain schema and does not
   create domains (§4.2).
3. Applications are global, identity is `(application_id, version)` (§4.3).
4. BBC-like domains are `INDEPENDENT`: snapshots have their own date period and
   `company_snapshot_id` is null. Company-tied domains stay 1:1 with the company snapshot (§6.8).
5. A bind instance is one July 2026 view: one GL/Revolver/TermLoan snapshot plus **all** BBC
   dates contained in that month — not one bind instance per BBC date (§3, §6.5).
6. Time-series field is `is_time_series` + `period_type` on a `DATETIME` dimension; import
   values must be UTC midnight at period start (§6.7–6.9).
7. PR split, especially keeping domain and snapshot-alignment changes in their own PRs (§10).
8. Anything missing from the use cases (CLI, OUTPUT-only attach, schema_hash drift detection).
)
