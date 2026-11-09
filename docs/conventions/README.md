# Conventions scope map

This folder holds conventions for `zyPlat` (the Python backend and CLI). This map records which
conventions are specific to this repo's stack and which could be shared by other repositories
(for example a microfrontend) if the project grows to several repositories.

It is a plan, not a restructure. Nothing moves until a second repository exists and needs a
shared rule.

## Classification

| Document | Scope | Notes |
| --- | --- | --- |
| `python-style.md` | Python-only | Black, ruff, mypy, docstrings, naming. Stays here. |
| `framework-conventions.md` | Python-only | FastAPI, SQLAlchemy, Click. Stays here. |
| `testing.md` | Split | Principles (pyramid, isolation, 80% gate, test when fixing bugs) are shared. Pytest fixtures, file layout, and the taxonomy/domain/company test areas are Python/zyPlat-only. |
| `code-comments.md` | Mostly shared | Rules (when to comment, TODO owner and date, no narration) apply everywhere. Examples are Python. Needs language-neutral examples to share. |
| `code-evolution.md` | Mostly shared | Boy Scout rule, refactor before extending, rewrite versus refactor. Examples are Python. |
| `code-reuse.md` | Split | DRY and premature-abstraction guidance is shared. CRUD base classes, SQLAlchemy mixins, and `app/` paths are Python-only. |
| `markdown-style.md` | Shared | Applies to Markdown in every repository. |

## Cross-repo rules currently inside `AGENTS.md`

These are written for this repo but would need one agreed version across repositories:

| Rule | Why it must match |
| --- | --- |
| Error response shape (machine-readable code, message, request/trace id) and the status-code mapping | The frontend parses it. |
| `request_id` propagation and log field names | Traces must join across services. |
| Terminology (`company`, `period_type`, `period_value`, `ord`) | Shared vocabulary in UI, API, and docs. |
| Documentation update rule (plans, schema docs, `AGENTS.md`) | Same workflow in every repository. |
| Commit, branch, and PR practices | Same workflow in every repository. |

The API contract (OpenAPI spec plus the error shape) is the first artifact worth sharing,
because a second repository depends on it directly.

## Proposed layout when a second repository exists

1. Each repository keeps its own short `AGENTS.md` and its own stack-specific conventions,
   because tools and agents read the repo they are working in.
2. Shared rules move to one small repository (for example `zyplat-conventions`) holding the
   shared documents above, with language-neutral examples.
3. Consuming repositories link to it or sync it in CI. Avoid git submodules unless a sync step
   proves too fragile.
4. Do not add a third copy of a rule. Keep the `.cursor/rules/` summary and the
   `docs/conventions/` reference pairing described in `AGENTS.md`.

## Before extracting anything

- Wait for the second repository's real needs. Rules extracted early tend to be wrong.
- Rewrite shared documents with examples in neutral pseudocode or one example per stack.
- Keep Python-only details (tooling versions, SQLAlchemy, FastAPI) out of the shared set.
