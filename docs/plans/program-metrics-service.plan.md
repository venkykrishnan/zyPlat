# Program and Metrics Service Plan (Draft v1.1) - vk feedback on 11 Nov 2026

Status: **awaiting review**. This plan follows `docs/Goals/ProgramAndMetric.md` steps 1–3.
Implementation (step 5) starts only after step 4 (your input).

This document reviews the goal and the ciqFE implementation, answers the open questions,
proposes the language, parser, engine and store, and splits the work into PRs. It does not
change runtime code.

Source studied: `ciqFE` at `ba4c2c4` (`src/parser/parsimmonParser.ts`,
`src/services/calculations/**`, `docs/parserDocs/*`, `input/programs/*`).

## 1) Goal and scope

Add **programs** (named, versioned collections of metrics written in **zml**, the zyPlat metrics
language) and a **metrics service** that defines them, binds them to application data,
calculates them and serves the values.

In scope:

- zml grammar, parser, AST, validation
- Program and metric definition, versioning, lifecycle, sharing across applications
- Provided versus calculated metric values at program scope
- Calculation engine producing a DataFrame, persisted as Parquet
- Value retrieval
- Import CLI (`.txt` and `.json`, consistent)
- Application changes needed to attach programs (ciqLet notion)

Out of scope (later, in stages, per the goal): thresholds, forecast, loan-schedule DSLs;
customer-book (cross-borrower) aggregation; the LLM-driven ciqLet configuration; the frontend.
The design below keeps room for all of them.

## 2) Review of the goal

### 2.1 What carries over from ciqFE

| ciqFE notion | zyPlat treatment |
| --- | --- |
| Program of metrics, `programName:scope:op { … }` | Kept, with a new header (see 4.1) |
| Parse, bind, calculate, persist | Kept as the four jobs of the metrics service |
| Metric `@domain` tag | Kept as an optional tag, no longer part of identity (see 4.2) |
| `TS` / `Gen` op types | `TS` kept. `Gen` (non-time-series) deferred, see open question 6 |
| Filters, `DAYS`, `BY`/`HAVING`, grouped reduce (BBC) | Kept, same semantics |
| Dynamic (in-memory) programs | Kept as an evaluate-without-persist endpoint (PR 8) |
| ciqLet (domains plus programs) | Becomes the existing `application`, extended with programs |
| CUST / BOR scopes and `#C: #B: #L:` qualifiers | Replaced by company scope (see 4.3) |
| STD / BASE scopes, system domains and taxonomies | Removed, per the goal |
| `SUM(BORROWER, …)` customer book | Deferred, needs company relationships (open question 7) |

### 2.2 What the goal changes

- **No system domains or taxonomies.** Everything a program reads is a configured domain bound
  through an application. A program therefore must declare which domains it reads.
- **A program is shared.** FinancialStatements is used by TermLoan and others. A program is
  not owned by one application. Applications attach program versions.
- **Provided versus calculated is first class.** See section 6.

## 3) Open questions, answered

### Q1. Improvements to the grammar

The ciq v2 grammar is coherent and proven, so zml is a **superset-compatible cleanup**, not a
redesign. Every ciqFE sample program (`input/programs/*.txt`) must still parse, either unchanged
or through the mechanical migration listed below. Suggested changes, with a recommendation on
each:

| # | Issue in ciq v2 | Suggestion | Breaking? |
| --- | --- | --- | --- |
| 1 | Assignment separator allows bare spaces, so `a = x - y b = 2` is ambiguous | Separator is newline or `;` only | Yes (rare in practice) |
| 2 | Metric identity mixes name, `@domain`, scope, `#C/#B/#L`, `#v` | Identity is `(program, version, name)`. `@domain` is an optional tag. Scope and company come from the bind, not the text | Header only |
| 3 | `MIN(a, b)` and `MIN(Domain:field)` share a name, forcing lookahead | Keep both forms for compatibility. Add `LEAST` / `GREATEST` for the scalar form and mark the old scalar form deprecated | No |
| 4 | No `NOT`, no `IN (…)`, no `BETWEEN`, no null test | Add `NOT`, `IN ("a", "b")`, `BETWEEN`, `IS NULL`. Today users chain several comparisons with AND/OR operators | No |
| 5 | Aggregate argument is a bare field. `SUM(AR:amount * rate)` is impossible | Allow a row-level expression as the aggregate value. Easy with columnar evaluation | No |
| 6 | Only `SUM AVG MIN MAX` | Add `COUNT`, `COUNT_DISTINCT`, `MEDIAN` | No |
| 7 | Time operators are keywords with default-agg forms (`MTH YTD(x)`, `PREV(x)`, `LTM(x)`) | Keep as is. Add `LAG(x, n)` and `LEAD(x, n)` generalising `PREV`/`NEXT` | No |
| 8 | System functions use a trailing `!` (`FIRSTPeriod!`) | Add function-call form `FIRST_PERIOD()`. Keep the old form | No |
| 9 | Every operator is a reserved keyword, so a dimension called `YTD` or `BY` breaks parsing | Contextual lexing: keywords are reserved only where the grammar expects them | No |
| 10 | `dimension_value` accepts a bare identifier as an enum value | Require quotes for strings. Bare identifiers only for field and metric references | Yes (rare) |
| 11 | No comments | `//` to end of line and `/* … */`. (`#` is avoided because of `#v`) | No |
| 12 | No period literals | Add `2026-01`, `2026-Q1`, `2026` literals and `a..b` ranges, needed for section 6 | No |
| 13 | No source positions in errors | Every AST node carries line and column. Parse errors name the expected token | No |
| 14 | Division by zero and missing values undefined | Define: division by zero gives null, null propagates through arithmetic, `COALESCE(x, y)` added | Defined, not changed |
| 15 | Balance-sheet "end value" rule hidden in the evaluator (`isEndValue`, balance-sheet account types) | Make it an explicit domain-metric attribute `rollup: SUM or END` so `YTD`/`LTM`/`QTR` behave from the domain definition | Domain schema change |
| 16 | Recursive `PREV(self)` works (Retained_Earnings) but the dependency rules are implicit | Specify: edges through `PREV` and `LAG` do not count as cycles. A cycle through current-period edges is a parse-bind error | Defined, not changed |
| 17 | `order` field in the JSON import | Drop it. Calculation order is derived from the dependency graph | JSON only |

Items 1, 2, 10 and 17 are the breaking ones. A `zyplat migrate-ciq` command converts ciq v2
programs to zml mechanically, and the sample corpus is a regression suite.

### Q2. Parser, framework, language for pandas/Parquet

**Recommendation: Python, in-process, parser by Lark, evaluator on pandas/NumPy.** Do not keep
the TypeScript engine as a sidecar.

The earlier ciqFE canvas argued to keep TypeScript because ciqFE computes on a document store
and a period-to-number map. zyPlat inverts that premise: the data is columnar (Parquet), the
product is time-series calculation, and the consumer wants a DataFrame. Running the engine
beside the data removes a second runtime, a process boundary, and a second grammar.

Parser options:

| Option | Verdict |
| --- | --- |
| **Lark** (EBNF-native, LALR or Earley, contextual lexer, source positions, good errors) | **Recommended.** The `.lark` file is near-line-for-line the existing EBNF, so the ciqFE grammar docs carry over. Supports several start rules and shared terminals, which suits the other DSLs |
| parsy | Closest to Parsimmon (combinators), easiest literal port. Weaker error messages, no grammar file to share or document |
| pyparsing | Workable, slower, error reporting weaker than Lark |
| ANTLR | Only option with a TypeScript target for a browser parser. Heavier toolchain and a Java build step. Reconsider only if the microfrontend must validate offline |
| Hand-written Pratt parser | Best errors and speed, but we own every grammar change. Not worth it for one grammar |

Frontend authoring: the microfrontend validates by calling `POST /programs/validate`, which
returns diagnostics with positions. That keeps one grammar. Revisit ANTLR only if latency or
offline editing becomes a requirement.

Engine design:

- Compile the AST into vectorised operations. Every expression evaluates to a **period series**:
  a `pandas.Series` indexed by `pandas.PeriodIndex`, evaluated for **all periods at once** (the
  ciqFE evaluator loops period by period).
- `SUM(AR:cond, amount)` becomes a boolean mask over the domain frame followed by a
  `groupby(period)`. `DAYS(a, b)` is a vectorised date difference. `BY key HAVING …` is a
  `groupby([period, key])`, a mask, then a sum. Concentration excess is
  `clip(lower=0)`, `minimum`, `sum` over groups.
- `YTD`, `LTM`, `QTD`, `PREV`, `YOY`, `MOM` are `rolling`, `shift` and `groupby(year)` on the
  series. `rollup: END` metrics skip summing and take the last value.
- Self-referencing `PREV` metrics (Retained_Earnings) are the exception. A metric in a
  strongly connected component through `PREV` edges is evaluated by an ordered period loop. All
  other metrics stay vectorised.
- The operator set is a **registry** (`name -> callable plus type rule`), so other DSLs add
  functions without touching the parser core.

### Q3. Other DSLs in ciqFE

ciqFE already has three more grammars: threshold, forecast, and loan schedule (plus
customer-book and filter extensions inside the metrics grammar). Design for them now, build them
later:

- `modules/zml/` holds the **language core**: shared lexical rules and expression grammar
  (`zml_core.lark`), the AST base, the diagnostics type, and the operator registry.
- `zml.lark` (programs) imports the core. `threshold.lark` and `forecast.lark` import the same
  core and add their own top-level statements. Each has its own start rule and its own module
  (`modules/threshold/`, `modules/forecast/`) that consumes calculated values.
- Rule of thumb from ciqFE: metric programs **compute** from existing data, thresholds
  **score** an existing series, forecasts **create** future periods. Only the first belongs to
  this goal.

### Q4. Shape of the metrics service

Two parts, one deployable for v1:

| Part | Responsibility | Interface |
| --- | --- | --- |
| **Define and calculate** (write side) | Program and metric CRUD, versioning, validation, bind, calculate, persist values | `modules/program/` (router, service, repository) plus `modules/zml/` |
| **Read values** (read side) | Query calculated values by bind instance, program, metric, period range | `MetricValueStore` protocol over Parquet, behind a separate read router |

Splitting the read side now costs only a protocol and a router. If read load or latency later
demands it, the read router can move to its own process, or DuckDB can be added for
cross-snapshot queries (already on the backlog), without touching the write side.

The service boundary from ciqFE holds: **the metrics service does not own source data.** It
receives a bind (a set of domain-instance snapshots) and reads frames through
`InstanceDataService`. It never reads files directly.

## 4) Proposed model

### 4.1 Program header and text form

```text
program FinancialStatements version 1.2.0 scope GLOBAL {
  uses GL, LoanPayment                 // domains this program reads

  Gross_Profit   = Revenue - Cost_of_Sales
  Gross_Margin   = Gross_Profit / Revenue
  Revenue@GL     = SUM(GL:accountType == "Revenue", amount)
  EBITDA         = Net_Income + Interest_Expenses + Tax_Expenses + Depreciation
}
```

- `scope` is `GLOBAL` or `COMPANY`, mirroring taxonomy and domain ownership. A company-scoped
  program carries `company: NorthCo` in its header.
- `uses` lists domains by `domain_id`. It is the program's **domain contract**.
- The old `name:SCOPE:TS #C:… {` header is accepted by the importer and rewritten.

### 4.2 Metric identity and references

- Identity: `(program, version, name)`.
- A bare name resolves in this order: metric in this program, then metric in a program the
  header names under `imports` (see 4.5). No store-wide scope precedence, because STD / BASE /
  CUST / BOR no longer exist.
- Qualified reference to another program: `FinancialStatements.EBITDA`.
- `@domain` after a name is an optional tag for grouping and output labelling.

### 4.3 Entities and tables

All new tables use Alembic migrations. New code lives in `backend/app/modules/program/` and
`backend/app/modules/zml/`, per `AGENTS.md`.

| Table | Purpose |
| --- | --- |
| `programs` | Logical program: `program_id`, `scope_type`, `owner_company_id` (null for GLOBAL), `status` (`DRAFT`, `PUBLISHED`, `ARCHIVED`), `default_version_id` |
| `program_versions` | `version`, source text, source hash, parser version |
| `program_domains` | Domains the version reads (`domain_definition_id`, required dimensions and metrics, schema hash). Same subset rule as `application_domains` |
| `program_imports` | Other program versions this version references, with `PINNED` or `LATEST_PUBLISHED` |
| `program_metrics` | `name`, `formula` text, `ast` (JSONB), `description`, `domain_tag`, dependency edges with `CURRENT` or `LAG` type |
| `application_programs` | Application version to program version, many-to-many. A program is shared by many applications |
| `program_runs` | One calculation: bind instance, program version, period plan, status, row count, storage pointer, checksum, `calc_run_id` |

Lifecycle mirrors application (asymmetric to taxonomy, by design): program-level
Draft / Publish / Archive and one default-version pointer. Published versions are immutable.

### 4.4 Domains the program reads

zyPlat has no system domains, so a program cannot assume `GL` exists. At attach time
(`application_programs`), the service checks the application's bound domains against
`program_domains`: kind, time-series dimension, dimension types, metric types. The check reuses
`validate_expected_against_domain` from `modules/application/validators.py`. A program that
needs domains the application does not provide cannot be attached.

### 4.5 Programs using programs

TermLoan can use FinancialStatements metrics. The `program_imports` rows record that. At bind
time the engine runs the imported program first (or reuses its stored run for the same bind) and
exposes its series to the importer. Cycles between programs are rejected at publish.

### 4.6 ciqLet as application

A ciqLet is an application with input and output domains plus programs. The application service
already has versions, lifecycle, company enablement and bind instances. This goal adds:

- `application_programs` (above)
- Output-domain linkage: a program's calculated series can be materialised as a snapshot of an
  OUTPUT domain of the application, so downstream applications consume it as ordinary domain
  data. Deferred to PR 7, see open question 8.
- Bind-and-run: from a bind instance, run all attached programs.

AI-driven ciqLet configuration is out of scope.

## 5) Calculation and storage

### 5.1 Store

| Data | Store | Reason |
| --- | --- | --- |
| Programs, versions, metrics, ASTs, links, run metadata | **PostgreSQL** (JSONB for ASTs) | Transactional, relational, matches existing services |
| Calculated metric values | **Parquet** through the existing `InstanceDataStore`, one immutable file per run | Columnar, DataFrame-native, same storage design as instance data; S3 backend arrives with the existing backlog item |

Value frame (long form, one row per metric and period):

| Column | Type | Notes |
| --- | --- | --- |
| `metric` | string | metric name within the program |
| `period` | string | period value, aligned to the bind's `period_type` |
| `value` | decimal / float64 | null when not computable |
| `source` | string | `PROVIDED` or `CALCULATED` |
| `provided_ref` | string null | where a provided value came from |

Long form keeps schema stable when metrics change and reads as a pivot when needed.

### 5.2 Run flow

1. Resolve the bind instance: company, snapshots, domains.
2. Load frames through `InstanceDataService.read_snapshot_frame` (only needed columns).
3. Apply the period plan (section 6).
4. Order metrics by dependency graph, evaluate, merge provided values.
5. Write the Parquet run file, commit `program_runs` pointer (write-then-commit, same orphan
   rules as instance data).
6. Return the run id. Reads go through the read side.

A failed run leaves no partial values. Runs are immutable. A re-run is a new run id, and the
default read resolves the latest successful run for a bind and program version.

## 6) Provided versus calculated

A metric value is either **provided** (an input) or **calculated** (from its formula). The
service supports both, per period, within one metric.

### 6.1 Period plan

A **period plan** is an ordered list of ranges, each marked `PROVIDED` or `CALCULATED`, over
the program's metrics:

```text
2026-01..2026-04  PROVIDED
2026-05..         CALCULATED
```

Default when no plan is given: all periods `CALCULATED`. Plans must not overlap. Periods
outside every range are an error unless a default is set.

### 6.2 Where provided values come from

From a bound INPUT domain with a **metric-value shape**: a time-series domain with a metric-name
dimension, the time-series dimension, and a `value` metric. This reuses existing domain and
snapshot machinery, so provided values are ordinary imports with ordinary lineage. A program
declares in `uses` which domain carries provided values.

### 6.3 Semantics

- For a `PROVIDED` period, a metric takes the provided value. If none exists for that metric
  and period, the value is null and a diagnostic is recorded (the plan said provided, the data
  did not supply it).
- For a `CALCULATED` period, the formula runs. Formulas may read provided values from earlier
  periods (`PREV(EBITDA)` in May reads April's provided value), because provided and calculated
  values live in one series.
- Every output row records `source`.
- Provided values are not recalculated, even if a formula exists.

### 6.4 Where the plan lives (needs your decision)

The example in the goal (EBITDA provided for Jan–Apr 2026 for a borrower, calculated from May)
is a **per-company, per-bind** fact. I recommend storing the plan on the **bind** (a run
parameter with a program-level default), not in the program definition, so one shared program
serves many companies with different plans. See open question 1.

## 7) API design

Routers follow `AGENTS.md`: no business logic, typed exceptions, the central error handler.

### 7.1 Definition (write side)

| Method and path | Purpose |
| --- | --- |
| `POST /programs` | Create program with first version (text or JSON body) |
| `GET /programs`, `GET /programs/{id}` | List, get default version |
| `POST /programs/{id}/versions` | Add a version |
| `GET /programs/{id}/versions/{version}` | Get a version with metrics |
| `PUT /programs/{id}/versions/{version}` | Update a DRAFT version |
| `POST /programs/{id}/publish`, `unpublish`, `archive`, `set-default` | Lifecycle |
| `POST /programs/validate` | Parse and bind-check text without saving. Returns diagnostics with line and column |
| `GET /programs/{id}/versions/{version}/export?format=txt` (or `json`) | Round-trip export |

### 7.2 Application attachment

| Method and path | Purpose |
| --- | --- |
| `PUT /applications/{id}/versions/{v}/programs/{program_id}` | Attach a program version (domain contract check) |
| `GET`, `DELETE` on the same path family | List, detach |

### 7.3 Run and read

| Method and path | Purpose |
| --- | --- |
| `POST /applications/{id}/versions/{v}/bind-instances/{bid}/runs` | Run attached programs for a bind. Body: optional program ids and period plan |
| `POST /programs/evaluate` | Dynamic run: zml text plus a bind id, returns a frame, optional persist |
| `GET /runs/{run_id}` | Run status and metadata |
| `GET /bind-instances/{bid}/metric-values` | Values by program, metric, period range. JSON by default, `Accept: text/csv` or Arrow later |

## 8) Import CLI

`zyplat program import <file>` accepts `.txt` (zml source) and `.json`. Both normalise to one
internal **program document** (name, version, scope, uses, imports, metrics). The JSON form:

```json
{
  "program": "FinancialStatements",
  "version": "1.2.0",
  "scope": "GLOBAL",
  "uses": ["GL"],
  "metrics": [
    { "name": "Gross_Profit", "formula": "Revenue - Cost_of_Sales", "description": "…" }
  ]
}
```

Consistency guarantees, enforced by tests:

- Text to document to text round-trips to equivalent ASTs.
- JSON to document to JSON is stable.
- The same program in both forms produces identical `program_metrics` rows and AST hashes.
- Errors from both paths use the same diagnostic shape.

Other commands: `program export`, `program validate`, `program run`, `migrate-ciq`.

## 9) Validation summary

| Check | Where |
| --- | --- |
| Grammar | `zml` parser |
| Name resolution (program, imports) | bind-check in service |
| Domain, dimension and field existence and types | bind-check against `program_domains` |
| No cycles through current-period edges; `LAG`/`PREV` cycles allowed | dependency graph |
| No cycles between programs | publish |
| Period literals match the domain period type | bind-check |
| Period plan non-overlapping and covers the run range | run |
| `DAYS` only on DateTime dimensions; no bare `DAYS` assignment | bind-check |

## 10) Tests

- **Parser**: every ciqFE sample (`BBC.txt`, `base_*_program.txt`, `sales_arr_std.txt`,
  `hr_headcount_std.txt`) parses; each grammar suggestion in Q1 has a positive and a negative
  case; diagnostics carry positions.
- **Round trip**: txt and JSON equivalence (section 8).
- **Evaluator**: golden-value tests per operator. BBC acceptance: reproduce the
  `BBCTerms` workbook outputs from ciqFE `docs/ExternalSpecs/bbc`. Property tests that
  vectorised results equal a scalar reference evaluator on random frames.
- **Provided vs calculated**: mixed series, `PREV` reading a provided value, missing provided
  value diagnostic, overlapping plan rejected.
- **Recursion**: Retained_Earnings-style self-referencing `PREV`.
- **Service and API**: lifecycle, attach contract check, shared program across two
  applications, run write-then-commit, failed run leaves no pointer.
- **Migration**: up/down and model-versus-migration check for new tables.
- Keep the 80% coverage gate.

## 11) PR split

| PR | Touches existing entities? | Contents |
| --- | --- | --- |
| **PR 1 — zml core** | No | `modules/zml/`: Lark grammar, AST, diagnostics, `validate` function, sample-corpus parser tests, `migrate-ciq` text transform |
| **PR 2 — Program definition** | No (new tables) | Tables, CRUD, versioning, lifecycle, import and export of txt/json, `POST /programs/validate` |
| **PR 3 — Evaluator** | No | Operator registry and pandas engine in tiers: arithmetic and `IF`; filtered aggregates and `DAYS`; time operators; `BY`/`HAVING` and grouped reduce; recursion. Pure functions over frames, no DB |
| **PR 4 — Provided vs calculated** | **Yes: domain-metric `rollup` attribute** | Period plan, provided-values domain shape, merge semantics, `source` column. Domain `rollup: SUM or END` migration |
| **PR 5 — Run and read** | No | `program_runs`, Parquet write through `InstanceDataStore`, run API, `MetricValueStore`, read API |
| **PR 6 — Application attachment** | **Yes: `application_*`** | `application_programs`, contract check, bind-and-run, AGENTS.md service list |
| **PR 7 — Output domains** | Yes | Materialise program output into OUTPUT-domain snapshots (if confirmed) |
| **PR 8 — CLI and dynamic evaluate** | No | `program` CLI group, `POST /programs/evaluate` |

Suggested order: 1 → 3 (in parallel with 2) → 4 → 5 → 6 → 8, then 7. PR 3 can be developed
against fixtures before PR 2 merges.

## 12) Documentation updates (when implementing)

Per `AGENTS.md`: update `docs/plans/taxonomy-domain-service.plan.md` and
`docs/plans/taxonomy-domain-v1-schema.md` (rollup attribute, new tables), `AGENTS.md` (V1
service list gains `program`; module layout adds `zml`), the matching conventions rule if one
changes, and `docs/plans/backlog.md`. Add `docs/parserDocs/zml-grammar.md` (the syntax
contract) alongside the `.lark` file.

## 13) Risks

- **Semantic drift from ciqFE.** Vectorising period-by-period logic can change edge cases
  (balance-sheet end values, sparse periods, first-period handling). Mitigation: golden tests
  from ciqFE outputs, and a scalar reference evaluator used only in tests.
- **Grammar ambiguity under LALR.** Items 3 and 10 in Q1 exist to avoid it. Fallback is Lark's
  Earley mode with a small performance cost.
- **Recursive metrics** need a per-period loop and are slower on wide ranges. Expected to be
  few.
- **Parquet-only values** make point queries slower than a row store. Acceptable for v1; DuckDB
  is the planned answer.

## 14) What this plan needs from you

1. Where does the **period plan** live (6.4): on the bind with a program default
   (recommended), or in the program definition?
2. Approve the **breaking** grammar items (Q1 items 1, 2, 10, 17) with a `migrate-ciq`
   converter, or keep strict ciq v2 compatibility for now?
3. Confirm **Python, Lark, pandas, in-process** (Q2), and that ANTLR/TypeScript are not needed
   for the microfrontend validation path.
4. Confirm **no CUST/BOR scopes**: a program is `GLOBAL` or owned by one company, and
   company-specific numbers come from the bind.
5. Confirm **provided values come from a bound INPUT domain** with a metric-value shape (6.2).
6. Is `Gen` (non-time-series program) needed in this goal, or only `TS`?
7. Is **customer-book aggregation** (`SUM(BORROWER, …)`) in scope here? It needs a company
   relationship (customer to borrowers) that zyPlat does not have yet.
8. Should program output be **materialised as OUTPUT-domain snapshots** (PR 7), or is the
   Parquet run enough for now?
9. Add the domain `rollup: SUM or END` attribute (Q1 item 15) now, or keep it implicit?
