# Project record

## Purpose

Build a personal-data map from SQL DDL: parse `CREATE TABLE` statements, classify columns by token-based name rules, flag special categories, and label tables as `subject`, `linked`, or `none` through foreign keys reachable from a subject table. The utility does not read production data values.

## Scope

- Parse `CREATE [TEMPORARY] TABLE [IF NOT EXISTS] [schema.]name (...)` from schema text, including double-quoted, backtick and `[bracket]` names.
- Record columns and both column-level `REFERENCES t(...)` and table-level `FOREIGN KEY (...) REFERENCES t(...)` declarations.
- Classify columns with `DEFAULT_RULES` or a supplied `Rule` sequence; support per-column overrides as `table.column` mapped to a category or `None`.
- Compute table roles by breadth-first search over references: `subject` when a `direct_identifier` or `name` column exists, `linked` when a subject table is reachable, `none` otherwise; `via` is the shortest path.
- Render JSON or Markdown and provide `python -m personal_data_map` with `--format` and repeatable `--fail-on`.
- Enforce limits: UTF-8 input at most 5,242,880 bytes by default, at most 2000 tables by default, and parenthesis depth at most 32.

## Out of scope

Reading data values, connecting to a database, `ALTER TABLE`, views, NoSQL schemas, legal basis, and retention fields. Classification is limited to column-name tokens and the foreign-key graph.

## Status

Version `0.1.0`. The public API exported by `personal_data_map` and the CLI entry point are implemented. Tests live in `tests/test_personal_data_map.py`.

## Constraints

Python 3.10 or newer; standard library only; no runtime dependencies; package name `personal_data_map`.

## Factory run u287 (measured from API usage)

| Date (UTC) | Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| 2026-11-10 | generation | deepseek-v4-pro | yes | 1672 | 27553 | 0 | 3328 | 0.0557 |
| 2026-11-10 | fix-1 | deepseek-flash | no | 12760 | 2658 | 0 | 80384 | 0.0038 |
| 2026-11-10 | fix-2 | deepseek-flash | no | 9683 | 712 | 0 | 37376 | 0.0020 |
| 2026-11-10 | audit | deepseek-flash | no | 16171 | 23879 | 0 | 240896 | 0.0175 |
| 2026-11-10 | fix-3 | deepseek-flash | no | 27738 | 8489 | 0 | 513536 | 0.0108 |
| 2026-11-10 | threat-model | deepseek-flash | no | 12447 | 6008 | 0 | 49536 | 0.0056 |
| 2026-11-10 | docs | deepseek-flash | no | 87600 | 10358 | 0 | 256 | 0.0194 |

Total: $0.1147. Prices: deepseek line, as measured by its adapter. Providers serve the current version of each model id, so the date tells which version answered; versions, launch stages and price sources per line are in the factory's model register (docs/MODELS.md).
