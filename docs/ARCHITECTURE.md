# Architecture

`personal_data_map` is a single stdlib-only package, `personal_data_map`, split into one public
module and a small CLI entry point.

## Pipeline

1. **Tokenize** (`_tokenize`): a hand-written scanner for identifiers, double-quoted, backtick and
   `[bracket]` quoted names, single-quoted strings with `''` escapes, `--` and `/* */` comments,
   numbers and punctuation. It tracks the line of every token so errors can name it.
2. **Parse** (`parse_ddl` / `_parse_create_table`): recognises `CREATE [TEMPORARY] TABLE
   [IF NOT EXISTS] [schema.]name ( ... )`, splits the top-level comma-separated items, and records
   column-level and table-level `REFERENCES`. Nested parentheses are bounded at depth 32 so hostile
   input cannot exhaust the stack or the loop. Statements that are not `CREATE TABLE` and
   `CREATE TABLE ... AS SELECT` are skipped.
3. **Classify** (`classify`): splits column names into lowercased tokens on `_`, `-`, spaces and
   camelCase boundaries, then applies `DEFAULT_RULES` in priority order. The first matching rule
   wins; `overrides` can clear or replace a column's category.
4. **Trace roles** (`classify`): builds a directed graph from `local column -> referenced table`,
   marks tables with a `direct_identifier`/`name` column as `subject`, and runs a breadth-first
   search to label every other reachable table `linked` with the shortest path in `via`.
5. **Render** (`render`): sorts JSON keys and indents by two spaces, or emits a Markdown table of
   categorised columns only.

## Boundaries

- No database connection, no data values, no `ALTER TABLE`, views or NoSQL schemas.
- Public API is exactly what `src/personal_data_map/__init__.py` exports in `__all__`.
- Errors are a single `MapError` carrying a machine-readable `code` and a message truncated to
  200 characters.

See [decisions](decisions/) for the choices that shaped this design.
