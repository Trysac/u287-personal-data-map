# Testing

Tests live in `tests/test_personal_data_map.py` and exercise the public API.

```sh
pytest tests/test_personal_data_map.py
```

## What the suite covers

- `parse_ddl` on a simple `CREATE TABLE` (`test_parse_simple`): table name, column names, and references.
- `classify` on a basic schema (`test_classify_basic`): column categories, table roles, and `special_category_tables`.
- Acceptance examples: `users.email` as `direct_identifier`; `users` as `subject`; `orders` and `audit` as `linked` with shortest `via` paths; whole-token matching for names such as `emailed_at`, `ship_date`, `latency_ms`, and `zipped_size`; `patients.diagnosis_code` as `special_category`.
- Parsing cases: quoted names, `--` comments, string literals containing `)`, skipped non-`CREATE TABLE` statements, `public.users`, `CREATE TABLE ... AS SELECT`, and MySQL `ENGINE=InnoDB` suffixes.
- Error paths: `input_too_large`, `parse_error` including the parenthesis depth limit, `too_many_tables`, `invalid_override`, and `invalid_rule`.
- Rendering: exact Markdown output for the `users` schema and sorted, two-space-indented JSON.
- CLI `main`: `--fail-on` matching a category, parse errors, usage errors, and IO errors.
- Edge cases: reference cycles, self-references, and schema-qualified names.
