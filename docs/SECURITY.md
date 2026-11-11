# Security

`personal_data_map` reads SQL schema text and never connects to a database or reads data values.

## Threat model

Defended:

- Oversized input: `parse_ddl` rejects UTF-8 input over `max_bytes` (default 5,242,880) with `input_too_large` before parsing.
- Excess tables: more than `max_tables` (default 2000) parsed tables raise `too_many_tables`.
- Deep nesting: parenthesis depth over 32 raises `parse_error`.
- Malformed or unterminated `CREATE TABLE` input: raises `parse_error` with the line of the `CREATE` statement.
- Error messages from `MapError` are truncated to 200 characters. Parser errors name a line, not input text.
- The library performs no implicit I/O; the CLI reads only the schema path supplied by the caller.

Not defended:

- Hostile schema text can still be up to 5 MiB and 2000 tables. Parsing is bounded but is not a sandbox.
- Column classification is name-token based. Missing or incorrect categories are not a security boundary and do not establish legal compliance.
- There is no authentication, authorization, database connection, or data access.
- The CLI reads any path the process can read, and output can contain schema identifiers. Protect schema files and generated maps according to the caller's environment.

## Reporting a vulnerability

Please open a private security advisory on the repository instead of filing a public issue. Include the input that triggers the problem and the `MapError` code you observed.
