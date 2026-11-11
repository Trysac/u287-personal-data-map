# Stack

| Concern | Choice | Notes |
|---|---|---|
| Language | Python >= 3.10 | Uses `from __future__ import annotations` and PEP 604 syntax. |
| Packaging | Hatchling (`pyproject.toml`) | `src/` layout, `py.typed` ships with the package. |
| Runtime dependencies | none | The parser, classifier and renderers are standard library only. |
| Lint and format | Ruff | `E`, `F`, `W`, `I`, `B`, `UP`, `SIM`, `S`, `RUF`; line length 100. |
| Types | mypy | `strict = true`, `files = ["src"]`. |
| Tests | pytest + pytest-cov | Branch coverage, `fail_under = 80`, `testpaths = ["tests"]`. |
| Docs gate | `docs-manifest.json` | Lists the documentation files a release must contain. |
| Secrets | gitleaks | Blocks committed credentials. |

There is no database driver, ORM or web framework: the library operates on schema text only.
