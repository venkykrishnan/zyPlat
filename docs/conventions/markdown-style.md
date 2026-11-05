# Markdown style

Applies to all Markdown in this repository (`*.md`), including goals, plans, conventions,
and `AGENTS.md`.

Tooling: [markdownlint](https://github.com/DavidAnson/markdownlint) via the
`davidanson.vscode-markdownlint` editor extension. Project defaults live in
`.markdownlint.json` at the repo root.

## Tables (MD060)

Use the **compact** column style everywhere:

- One space after every opening `|` and before every closing `|`
- One space on each side of cell content
- Delimiter rows use spaces around the dashes: `| --- | --- |`
- Do **not** use tight delimiters (`|---|---|`) or tight cells (`|Choice|Value|`)
- Do **not** pad cells to vertically align columns unless a table is already `aligned` and you
  keep the whole table in that style (prefer compact for new tables)

```markdown
<!-- BAD: tight delimiter with spaced cells (MD060) -->
| Choice | Value |
|---|---|
| Language | Python 3.12 |

<!-- GOOD: compact -->
| Choice | Value |
| --- | --- |
| Language | Python 3.12 |
```

Three-column tables use `| --- | --- | --- |` as the delimiter.

Leading and trailing pipes are required on every table row.

## Blank lines around blocks

- One blank line before and after ATX headings (MD022)
- One blank line before and after fenced code blocks (MD031)
- One blank line before and after lists when they sit next to other content (MD032)
- One blank line before and after tables (MD058)

```markdown
<!-- GOOD -->
## Technology choices

| Choice | Value |
| --- | --- |
| Language | Python 3.12 |

TIME_SERIES instance rows stay in Parquet.
```

## Headings

- Use ATX headings (`#`, `##`, …), not Setext underlines (MD003 / MD018–MD019)
- Put a space after the `#` markers (MD018)
- One top-level `#` title per file (MD025)
- Nest headings without skipping levels (MD001); do not jump from `##` to `####`
- Prefer unique heading text within a file when practical (MD024); if a repeated
  heading is intentional, keep the wording identical only when the structure needs it

## Fenced code

- Fence with triple backticks
- Always set a language tag when the fence holds code (`python`, `bash`, `sql`, `text`,
  `json`, …) (MD040)
- Use `text` for prose examples or ASCII diagrams that are not a real language
- Do not indent the fence markers themselves as part of a list item unless the code
  belongs inside that list item

````markdown
<!-- BAD -->
```
print("hi")
```

<!-- GOOD -->
```python
print("hi")
```
````

## Lists and emphasis

- Unordered lists use `-` consistently (MD004)
- Indent nested list content by 2 spaces
- Put a space after list markers (MD030)
- Prefer `**bold**` and `_italic_` over `__` / `*` mixtures within a document

## Line length and wrapping

Hard line wrapping is **not** required for Markdown in this repo. Long table cells, URLs,
and plan prose may exceed 80 columns. MD013 is disabled in `.markdownlint.json` for that
reason. Still:

- Prefer readable paragraph breaks over very long run-on sentences
- Break long shell or code examples with normal wrapping inside fences when it helps review

## Whitespace and file endings

- No trailing spaces on lines (MD009)
- No multiple consecutive blank lines (MD012); one blank line is enough
- Files end with a single newline (MD047)
- No hard tabs; use spaces (MD010)

## Links and references

- Prefer inline links `[label](path)` for local docs
- Use relative paths from the current file (`docs/plans/...`, `../Goals/...`)
- Link destinations must resolve; do not leave empty `[]()` placeholders in committed docs

## Review comments in source

If a Markdown review extension inserts HTML comment markers (for example `<!-- mdr ... -->`
or gutter review notes), strip resolved markers before merge unless the plan explicitly
keeps them as an AI revision brief for an open change.

## Checklist before finishing a Markdown change

1. Tables use compact pipes and `| --- | --- |` delimiters
2. Headings, fences, lists, and tables have surrounding blank lines where required
3. Fenced blocks have a language tag
4. No trailing whitespace; file ends with one newline
5. Editor markdownlint shows no errors on the touched files
