# Instance Data Storage (Design Note)

Status: **Accepted for v1** (local filesystem backend). Sections 1 to 6 are the original
proposal; section 7 records what was built and where it deliberately differs.

## 1. Problem

Domain instance data is currently modelled as one Postgres row per observation in
`domain_instance_entities`, with `dimensions` and `metrics` stored as JSONB.

This fits poorly with the expected usage of time-series instances:

- Instances will often be produced by a calculation engine, in bulk, one snapshot at a time.
- Updates are infrequent and replace a whole snapshot (a new `ord`), never edit rows in place.
- Writes and reads are columnar in nature, and consumers want a pandas DataFrame.

Costs of the current model for that workload:

- Per-row overhead: UUID primary key, two timestamps, two foreign keys, and index entries.
- JSONB repeats every key name in every row and loses dtypes (decimals, dates).
- Building a DataFrame requires unpacking JSON per row and re-casting types.
- Bulk replacement means millions of inserts, or delete plus reinsert, with MVCC bloat.

No API or CRUD code writes to these tables yet, so changing direction has no migration cost.

## 2. Proposal

Split responsibilities between Postgres and file storage.

1. **Postgres holds metadata only**: domain definitions, instances, snapshot associations, and
   lineage. Each `domain_instance_snapshots` row gains a storage pointer:
   - `storage_uri`
   - `row_count`
   - `schema_hash` (hash of the dimension and metric definitions the file was written with)
   - `checksum`
   - `calc_run_id` (nullable; identifies the producing run)
2. **TIME_SERIES data is stored as one immutable Parquet file per snapshot**, for example
   `{domain_id}/{company_id}/{period_type}/{period_value}/ord={ord}.parquet`.
   The Arrow schema is generated from the domain's dimension and metric data types so dtypes
   are preserved.
3. **Access goes through a storage interface** (a `Protocol`), so services and tests do not
   depend on the backend:
   - `write_frame(snapshot_id, df) -> StoredFrameInfo`
   - `read_frame(snapshot_id, columns=None, filters=None) -> pd.DataFrame`
4. **Validation happens at write time in the service layer**: columns match the domain
   definition, data types are correct, required fields are present, and taxonomy-bound
   dimensions only contain valid entity values.
5. **Write order**: write the file to a temporary path, move it into place, then commit the
   Postgres pointer. A crash leaves only an orphan file, never a dangling pointer. A cleanup job
   removes orphans.
6. **SCALAR domains** stay in Postgres JSONB for now. Add a per-domain `storage_backend` option
   only when there are two real backends to choose between.

## 3. Alternatives considered

- **Keep JSONB rows.** Fine for small volumes and ad hoc SQL filtering, but the wrong shape for
  bulk columnar workloads.
- **Typed columns per domain in Postgres.** Requires runtime DDL, which `AGENTS.md` prohibits.
- **TimescaleDB or ClickHouse.** Heavier than needed until query load shows a need.
- **Table formats such as Delta or Iceberg.** Revisit if merge or time-travel needs go beyond
  immutable per-snapshot files.

## 4. Trade-offs

- No SQL joins against instance data inside Postgres. Cross-file queries use DuckDB over Parquet
  if needed.
- No row-level updates. Corrections produce a new snapshot (`ord`).
- Database constraints no longer enforce instance data integrity, so write-time validation
  carries that responsibility and needs thorough tests.
- Deployment: the repo targets Render and AWS ECS. S3 fits ECS, but Render has no object store,
  so it would need local disk or an external bucket.

## 5. Interchange format and dtypes

- Use Arrow as the interchange format. In pandas, use nullable or pyarrow-backed dtypes so
  integers with nulls are not coerced to floats.
- Monetary metrics use decimal types, not float.
- Dates and periods use native date types, not strings.

## 6. Open questions

- Expected rows per snapshot (thousands, millions, or more).
- Whether consumers read through the API or run SQL directly.
- Whether a Render deployment must support this, and where files live there.
- Retention: how long superseded snapshots (older `ord` values) are kept.

## 7. As implemented (v1)

Code: `backend/app/storage/instance_data/` (schema, validation, store) and
`backend/app/services/instance_data.py`. Migration: `20261031_0002`.

### Differences from the proposal

- **Keys use surrogate ids**, `{domain_definition_id}/{instance_id}/{snapshot_id}.parquet`, not
  domain, period, and `ord` values. Ids never change, so renaming a definition cannot orphan
  files. `storage_uri` is `local://<key>`, relative to `INSTANCE_DATA_DIR`, so the root can move.
- **Interface** is `write(key, table)`, `read(uri, columns, filters)`, `delete(uri)` on Arrow
  tables. DataFrame conversion and validation live above the store, which keeps a future S3
  implementation small.
- **Write-once is enforced**, not just conventional: the file is written to a temp path and
  claimed with `os.link`, which fails if the target exists. A losing writer gets `ConflictError`.
- **Pointer columns are all-or-nothing** (DB check constraint), `storage_uri` is unique, and
  `row_count >= 0`. `domain_instance_snapshots.company_snapshot_id` is `NOT NULL` and unique per
  instance, as the schema doc always said (the model had drifted).
- **Write ordering**: validate, write file, commit pointer. If the commit fails the file is
  deleted; if that delete also fails it is logged and left for the orphan cleanup job (not built).

### Type and validation rules

| Domain type | Arrow type |
|---|---|
| STRING, ENUM | `string` |
| NUMBER | `float64` |
| INTEGER | `int64` |
| BOOLEAN | `bool` |
| DATE | `date32` |
| DATETIME | `timestamp[us, UTC]`; naive values are interpreted as UTC |
| ARRAY_STRING | `list<string>` |
| DECIMAL (metric) | `decimal128(38, 10)`; values with more than 10 decimal places are rejected, not rounded |

- Required columns are non-nullable in the file schema and checked for nulls.
- Conversion is strict. Lossy input is rejected: fractional floats in INTEGER, floats in
  DECIMAL, non-booleans in BOOLEAN, datetimes with a time of day in DATE.
- Unknown and duplicate columns are rejected; column order in the frame does not matter.
- Taxonomy-bound dimensions are checked against caller-supplied allowed values. Taxonomy
  version resolution (published, default, pinned) is not implemented, so callers resolve them.
- All problems in a frame are reported in one `ValidationError` (`details`).

### Usage

```python
service = InstanceDataService(get_instance_data_store())
service.write_snapshot_frame(db, snapshot_id, df, SnapshotWriteOptions(calc_run_id="run-42"))
df = service.read_snapshot_frame(db, snapshot_id, columns=["account", "amount"])
```

Reads return pyarrow-backed dtypes, so nullable integers and decimals survive.

### Known limitations

- **Ephemeral storage on containers.** The local backend writes to `INSTANCE_DATA_DIR`. On Render
  or ECS without a persistent disk, files vanish on redeploy while pointers remain. Use a
  persistent volume until the S3 backend exists.
- No API endpoints yet; the service is only callable from code.
- No orphan-file cleanup job and no retention policy for superseded snapshots.

## 8. Follow-on work

Tracked in `backlog.md`.
