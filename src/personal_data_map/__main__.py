"""Command-line interface for mapping personal data in a SQL schema."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import MapError, classify, parse_ddl, render


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m personal_data_map``."""
    parser = argparse.ArgumentParser(
        prog="python -m personal_data_map",
        description="Map personal data in a SQL schema from DDL.",
    )
    parser.add_argument("schema", help="Path to the SQL schema file.")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--fail-on",
        action="append",
        default=[],
        metavar="CATEGORY",
        help="Fail with exit code 1 if this category is present (repeatable).",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    try:
        ddl_text = Path(args.schema).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error reading {args.schema}: {exc}", file=sys.stderr)
        return 2

    try:
        tables = parse_ddl(ddl_text)
    except MapError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    data_map = classify(tables)
    rendered = render(data_map, args.format)
    print(rendered, end="" if rendered.endswith("\n") else "\n")

    if args.fail_on:
        fail_categories = set(args.fail_on)
        if any(
            ci.category in fail_categories for ci in data_map.columns if ci.category is not None
        ):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
