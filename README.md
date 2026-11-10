# personal-data-map

[![PyPI version](https://img.shields.io/pypi/v/trysac-personal-data-map)](https://pypi.org/project/trysac-personal-data-map/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-personal-data-map)](LICENSE)
[![CI](https://github.com/Trysac/u287-personal-data-map/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u287-personal-data-map/actions/workflows/ci.yml)

Map personal data in SQL schemas: parse CREATE TABLE statements, classify columns by token-based name rules, flag special categories and trace subject links via foreign keys

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-personal-data-map
# or
uv add trysac-personal-data-map
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import personal_data_map

# normalize() trims surrounding whitespace and lower-cases the text.
print(personal_data_map.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    personal_data_map.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
