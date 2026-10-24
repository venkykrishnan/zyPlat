# Plan: Taxonomy and domain service

This plan answers the open questions in [TaxonomyAndDomain.md](../Goals/TaxonomyAndDomain.md) and is the design the service implements.

## Resolutions

### 1. Recommended structure

One modular service, two aggregates, one relational database. Taxonomies and domains share classification inheritance, publication, and "which values are legal on an instance," so splitting them into separately deployed services would duplicate those rules without a scaling reason. Configuration data is small, highly relational, and always edited inside a transaction (publish a version, pin it, admit a value).

```text
HTTP (FastAPI)
  taxonomies  ──► Taxonomy aggregate
  domains     ──► Domain aggregate
                    │
                    ▼
            classification + hierarchy rules
                    │
                    ▼
            SQLAlchemy  ──► PostgreSQL
```

**Taxonomy aggregate**

- A taxonomy is an identity: name, description, and whether it is hierarchical. `isHierarchical` is fixed at creation.
- Configuration that can change (the allowed classification names, and the entities) lives on a **version**.
- A version is either `draft` or `published`. Published versions are immutable.
- There is at most one draft. The first version is a draft. `POST .../publish` freezes it. Further edits require `POST .../draft`, which clones the latest published version into version N+1.
- Entities belong to a version. `code` is the stable business key (unique within a version). Database ids are new on each clone, so clients address entities by code.
- Classifications stored on an entity are the ones assigned **directly** to it. Effective classifications are computed: walk from the root to the entity and union the direct values, first-seen order, no duplicates. Children do not store inherited values. Adding `CIQ` to a parent immediately shows up on every descendant's `effectiveClassifications`.
- A direct classification list is only additive relative to ancestors. The API cannot record an exception that strips a parent classification.
- An entity with an empty effective set is a **base** entity. `base` is not a stored classification name; that word is reserved.
- Hierarchical taxonomies are a single tree: exactly one root (`parentCode` null), every other entity has a parent, no cycles. The root is created first. This is checked on every write and again at publish. Flat taxonomies reject parent links.
- A hierarchical taxonomy cannot be published until it has its root.

**Domain aggregate**

- A domain is a named definition plus one or more **dimensions**. Each dimension pins a taxonomy and a **published** version. Omitting the version resolves it to the latest published version at that moment and stores the number. It is not a floating "always latest" pointer. A draft version cannot be pinned.
- The domain's inherited classifications are the union of `allowedClassifications` on those pinned versions, in dimension order, then declaration order, duplicates removed.
- A domain **instance** selects a subset of those inherited classifications (the subset may be empty). Base is always allowed and is not listed. The instance copies the dimension pins, so a later edit to the domain definition does not change existing instances.
- An instance **entity** supplies a value for every dimension (a taxonomy entity code) plus its own code, name, and an optional JSON `attributes` object.
- A taxonomy entity is a legal dimension value when it is base, or when its effective classifications intersect the instance's selected classifications. An entity tagged `[CIQ, EDGAR]` is legal on a CIQ-only instance because it is classified as CIQ. An entity tagged only `[EDGAR]` is not. Subset semantics (every tag on the entity must be selected) was rejected: the goal's inheritance example forces descendants of `Revenue [CIQ, EDGAR]` to keep both tags, and those descendants would otherwise be unusable on a single-classification instance.

References from domains and instances use `ON DELETE RESTRICT`. Deleting a taxonomy that is still pinned returns 409.

### 2. Can this support ciqFE taxonomies and domains?

The [ciqFE](https://github.com/venkykrishnan/ciqFE) repository was not readable from this environment (GitHub returned 404), so this mapping is from the differences the goal describes, not from a source audit.

Yes, as a data load, not as a binary-compatible API.

| ciqFE idea | What the input has to become |
| --- | --- |
| Standard taxonomies and domains that are not configurable | Ordinary rows. Nothing is built in. |
| `isSOR` boolean on an entity | A classification the operator names. Use `SOR` unless ciqFE used another word. `isSOR: true` → `classifications: ["SOR"]`. `isSOR: false` → `classifications: []` (base). Declare `SOR` on the taxonomy's `allowedClassifications`. |
| Hierarchical taxonomy such as `accountType` | `isHierarchical: true` and exactly one root. If the source has no root, add a synthetic root and parent the current top-level nodes under it. If it has several roots, either add that synthetic root or choose one and reparent the others. |
| Parent links and entity identity | Stable `code` values, unique inside the taxonomy. Names stay display names. |
| Configurable domain dimension (inventory class, GL account type) | A dimension whose `taxonomyName` (or id) points at that taxonomy. |
| Unpublished or unversioned source | Import entities into the draft, then publish. Domains can pin only a published version. First import is version 1. |
| A domain instance that "uses SOR" or "uses CIQ" | `classifications` on the instance lists those names. Base entities remain legal without being listed. |
| Flags other than `isSOR` | Another classification name if the flag restricts which instances may use the entity. Extra payload that is not a taxonomy goes on the instance entity's `attributes`. |

Load order: taxonomies and their entities, publish, domains with pins, instances with a classification selection, then instance entities. Codes that are only display labels with spaces or punctuation have to be given identifier codes (`productRevenue`); the human label goes in `name`.

This service does not model read-only system taxonomies, a live "track latest published version" pin, multiple roots, or auth. Those are the gaps to decide before calling the mapping done.

### Other design choices

- **Auth, tenants, and audit history of field diffs** are out of scope. `createdAt` and `updatedAt` are the only timestamps besides `publishedAt`.
- **Lists are unordered configuration sets**, returned in full (by name, or tree preorder for hierarchical entities). No cursor pagination.
- **Identifiers** (`name` on taxonomies, domains, dimensions, instances; `code` on entities) match `^[A-Za-z][A-Za-z0-9_-]{0,127}$`. Classification names use the same shape with a max length of 64, and `base` is reserved. Comparison is case-sensitive.
- **Display `name` on an entity** is free text, 1–256 characters. **Description** is optional, up to 4000 characters.
- **Rename** of a taxonomy or domain is allowed. Pins store ids, so a rename does not break them.
- **`isHierarchical` does not change** after create. **Allowed classifications** change only on a draft, and a name cannot be removed while a draft entity still lists it directly.
- **Schema lifecycle:** tables are created from the SQLAlchemy metadata on startup. That is acceptable while there is no production data. Alembic should land before the first real data load; `create_all` will not alter tables that already exist.

## Stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.12 |
| HTTP | FastAPI, Pydantic v2, OpenAPI at `/docs` |
| Persistence | PostgreSQL in any shared environment. SQLAlchemy 2 talks to it through `ZYPLAT_DATABASE_URL` (`postgresql+psycopg://...`, extra `postgres`). |
| Local and tests | SQLite, same models and services. Foreign keys are enabled. Tests use an in-memory database per test. |
| Server | uvicorn (`zyplat` / `python -m zyplat.main`) |

Python keeps the service and its tests in one language and runs without a database daemon. The model is ordinary relational data (uniqueness, restricted deletes, a transaction around publish and clone), which is PostgreSQL's job once more than one process is writing. SQLite is the same schema, not a second model.

## API

Base path `/api/v1`. JSON is camelCase. Errors:

```json
{ "error": { "code": "draft_required", "message": "...", "details": {} } }
```

Request-shape failures are HTTP 422 `validation_error`. Domain rule failures are 400. Missing resources are 404. Conflicts (duplicate name or code, edit of a published version, delete that is still referenced) are 409.

### Taxonomies

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/taxonomies` | Create identity and draft version 1 |
| GET | `/taxonomies` | List |
| GET | `/taxonomies/{id}` | Identity, latest version, latest published version number |
| PATCH | `/taxonomies/{id}` | Name, description; `allowedClassifications` only while a draft is open |
| DELETE | `/taxonomies/{id}` | Reject when a domain or instance still pins a version |
| POST | `/taxonomies/{id}/publish` | Freeze the draft |
| POST | `/taxonomies/{id}/draft` | Clone the latest published version into a new draft |
| GET | `/taxonomies/{id}/versions` | Version summaries |
| GET | `/taxonomies/{id}/versions/{version}` | One summary |
| GET | `/taxonomies/{id}/entities?version=&classification=` | Entities of a version. Default version is the latest. `classification=base` or a name filters on **effective** classifications |
| POST | `/taxonomies/{id}/entities` | Add an entity to the draft |
| GET | `/taxonomies/{id}/entities/{code}?version=` | One entity |
| PATCH | `/taxonomies/{id}/entities/{code}` | Draft only: name, parent, direct classifications |
| DELETE | `/taxonomies/{id}/entities/{code}` | Draft only; reject when it has children |

Entity JSON includes `classifications` (direct), `effectiveClassifications`, `isBase`, `parentCode`, and `depth`.

### Domains

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/domains` | Definition and dimensions (`taxonomyId` or `taxonomyName`, optional `version`) |
| GET | `/domains` | List |
| GET | `/domains/{id}` | Definition, dimensions, `inheritedClassifications` |
| PATCH | `/domains/{id}` | Name, description, or a full replacement of `dimensions` |
| DELETE | `/domains/{id}` | Reject while any instance exists |
| POST | `/domains/{id}/instances` | Instance. Body: `name`, `classifications` (subset of inherited) |
| GET | `/domains/{id}/instances` | List |
| GET | `/domain-instances/{id}` | Instance, including its snapshotted dimensions |
| PATCH | `/domain-instances/{id}` | Name or `classifications`. Narrowing the set is rejected when an existing entity would become illegal |
| DELETE | `/domain-instances/{id}` | Deletes its entities |
| POST | `/domain-instances/{id}/entities` | Body: `code`, `name`, `dimensions` map of dimension name → taxonomy code, optional `attributes` |
| GET | `/domain-instances/{id}/entities` | List |
| GET | `/domain-instances/{id}/entities/{code}` | One |
| PATCH | `/domain-instances/{id}/entities/{code}` | Name, dimensions, attributes. `code` is immutable |
| DELETE | `/domain-instances/{id}/entities/{code}` | Delete |
| GET | `/domain-instances/{id}/dimensions/{name}/values` | Taxonomy entities that are legal for that dimension on this instance |

`GET /health` returns `{"status":"ok"}`.

## Worked example

`accountType` is hierarchical with allowed classifications `CIQ` and `EDGAR`. Root `accountType` is base. Child `revenue` is directly `[CIQ, EDGAR]`. Child `productRevenue` stores `[]` and its effective classifications are `[CIQ, EDGAR]`. Sibling `expense` is base. Sibling `edgarOnly` is directly `[EDGAR]`.

Publish that version. Domain `generalLedger` has dimension `accountType` pinned to it, so the domain inherits `[CIQ, EDGAR]`. Instance `ciqGl` selects `[CIQ]`.

| Dimension value | On `ciqGl` |
| --- | --- |
| `productRevenue` | Allowed (effective set contains CIQ) |
| `expense` | Allowed (base) |
| `edgarOnly` | Rejected |

Opening a later draft and clearing `revenue`'s classifications changes the draft only. The instance still reads the published version it pinned.

## Tests

Unit tests cover effective-classification union order, dedupe, cycle detection, tree rules (no root, two roots, disconnect, flat parent), and the admissibility rule.

API tests drive the account-type / general-ledger story above, plus publish immutability, draft clone, version pinning (default latest published, reject a draft pin), classification edit rules, hierarchy write rules, domain and instance CRUD, and deletes that are still referenced.

Run `pytest` from the repo root after `pip install -e ".[dev]"`.

## Follow-ups, not in this build

- Alembic migrations before the first persisted environment.
- Bulk entity import for a ciqFE extract.
- Auth and a tenant boundary, if instances from different ledgers share one deployment.
- A floating pin that means "latest published" for callers who want that instead of a stored version number.
