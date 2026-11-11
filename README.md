# personal-data-map

[![PyPI version](https://img.shields.io/pypi/v/trysac-personal-data-map)](https://pypi.org/project/trysac-personal-data-map/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-personal-data-map)](LICENSE)

Map personal data in SQL schemas: parse CREATE TABLE statements, classify columns by token-based name rules, flag special categories and trace subject links via foreign keys

## Problem

Records of processing and privacy reviews need an inventory of which tables hold personal data, but hand-written inventories go stale with every migration. Scanning data values requires production access. This library works from DDL instead: it parses `CREATE TABLE` statements, classifies columns by name tokens, and marks tables that hold personal data only because their foreign keys reach a subject table.

## Install

```sh
pip install trysac-personal-data-map
# or
uv add trysac-personal-data-map
```

Requires Python 3.10 or newer. No runtime dependencies. Distribution name: `trysac-personal-data-map`; import name: `personal_data_map`.

## Usage

```python
from personal_data_map import classify, parse_ddl, render

tables = parse_ddl("""
CREATE TABLE users (id INT PRIMARY KEY, email VARCHAR(255));
CREATE TABLE orders (id INT, user_id INT REFERENCES users(id));
""")
data_map = classify(tables)
print(render(data_map, "markdown"))
```

`users` is a `subject` table; `orders` is `linked` with `via=['users']`. The CLI is `python -m personal_data_map schema.sql --format markdown --fail-on special_category`.

## Public API

- `Table(name, columns, references)` is a frozen dataclass; `references` contains `(local_column, referenced_table)` pairs.
- `parse_ddl(text, *, max_bytes=5_242_880, max_tables=2000) -> list[Table]` parses `CREATE [TEMPORARY] TABLE [IF NOT EXISTS] [schema.]name (...)` and records column-level and table-level `REFERENCES`.
- `Rule(category, tokens)` and `DEFAULT_RULES` define eight categories in priority order: `special_category`, `direct_identifier`, `name`, `date_of_birth`, `contact_address`, `online_identifier`, `financial`, `location`.
- `classify(tables, *, rules=DEFAULT_RULES, overrides=None) -> DataMap` returns `columns`, `roles`, and `special_category_tables`. Roles are `subject`, `linked`, or `none`; `via` lists the shortest reference path ending at a subject table. Override keys are lowercase `table.column`; values are a category from the active rules or `None`.
- `render(data_map, fmt)` supports `json` (sorted keys, two-space indent) and `markdown` (only columns with a category). Unsupported formats raise `ValueError`.

Errors use `MapError(code, message)` with codes `input_too_large`, `parse_error`, `too_many_tables`, `invalid_override`, and `invalid_rule`; messages are truncated to 200 characters. `parse_ddl` rejects UTF-8 input over 5,242,880 bytes and more than 2000 tables; parenthesis nesting over depth 32 raises `parse_error`. The library never connects to a database.

## Why not value scanners

A value scanner needs production data access. `personal_data_map` works from schema text alone and finds tables that are personal data only through a foreign key to a subject table. It cannot infer a personal-data column whose name does not match the configured token rules.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE)
