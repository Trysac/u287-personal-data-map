"""Map personal data in SQL schemas from DDL alone.

``personal_data_map`` parses ``CREATE TABLE`` statements, classifies columns by
name tokens, and traces which tables hold personal data only through foreign
keys reachable from a subject table.
"""

from __future__ import annotations

import json
import logging
import re
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "DEFAULT_RULES",
    "ColumnInfo",
    "DataMap",
    "MapError",
    "Role",
    "Rule",
    "Table",
    "__version__",
    "classify",
    "parse_ddl",
    "render",
]

__version__ = "0.1.0"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class MapError(Exception):
    """Base error for the personal_data_map package."""

    def __init__(
        self,
        code: Literal[
            "input_too_large",
            "parse_error",
            "too_many_tables",
            "invalid_override",
            "invalid_rule",
        ],
        message: str = "",
    ) -> None:
        self.code = code
        self.message = (message or "")[:200]
        super().__init__(f"[{self.code}] {self.message}")


@dataclass(frozen=True)
class Table:
    """A parsed CREATE TABLE statement."""

    name: str
    columns: list[str]
    references: list[tuple[str, str]]


@dataclass(frozen=True)
class Rule:
    """A classification rule.

    ``tokens`` contains one or more token phrases. A phrase matches when its
    name tokens appear contiguously in a column's name tokens.
    """

    category: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class ColumnInfo:
    table: str
    column: str
    category: str | None


@dataclass(frozen=True)
class Role:
    role: Literal["subject", "linked", "none"]
    via: list[str]


@dataclass(frozen=True)
class DataMap:
    columns: list[ColumnInfo]
    roles: dict[str, Role]
    special_category_tables: list[str]


DEFAULT_RULES: tuple[Rule, ...] = (
    Rule(
        "special_category",
        (
            "health",
            "diagnosis",
            "religion",
            "ethnicity",
            "sexual orientation",
            "biometric",
            "political",
            "union member",
            "genetic",
        ),
    ),
    Rule(
        "direct_identifier",
        (
            "email",
            "phone",
            "mobile",
            "ssn",
            "national id",
            "passport",
            "tax id",
            "dni",
        ),
    ),
    Rule(
        "name",
        ("first name", "last name", "full name", "surname", "given name"),
    ),
    Rule(
        "date_of_birth",
        ("dob", "birth date", "date of birth", "birthdate"),
    ),
    Rule(
        "contact_address",
        ("address", "street", "city", "postal code", "zip", "zipcode"),
    ),
    Rule(
        "online_identifier",
        ("ip", "ip address", "device id", "cookie id", "user agent"),
    ),
    Rule(
        "financial",
        ("iban", "card number", "account number", "salary"),
    ),
    Rule("location", ("latitude", "longitude", "lat", "lng")),
)


@dataclass(frozen=True)
class _Token:
    kind: Literal["identifier", "quoted", "string", "punct", "eof"]
    value: str
    line: int


def _is_name_token(tok: _Token) -> bool:
    return tok.kind in ("identifier", "quoted")


def _is_keyword(tok: _Token, word: str) -> bool:
    return tok.kind in ("identifier", "quoted") and tok.value.upper() == word


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    line = 1
    n = len(text)

    while i < n:
        ch = text[i]

        if ch in " \t\r\n":
            if ch == "\n":
                line += 1
            i += 1
            continue

        if ch == "-" and i + 1 < n and text[i + 1] == "-":
            j = i + 2
            while j < n and text[j] != "\n":
                j += 1
            i = j
            continue

        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            j = i + 2
            while j < n:
                if text[j] == "\n":
                    line += 1
                if j + 1 < n and text[j] == "*" and text[j + 1] == "/":
                    j += 2
                    break
                j += 1
            else:
                j = n
            i = j
            continue

        if ch == "'":
            j = i + 1
            out: list[str] = []
            while j < n:
                if text[j] == "'":
                    if j + 1 < n and text[j + 1] == "'":
                        out.append("'")
                        j += 2
                        continue
                    j += 1
                    break
                if text[j] == "\n":
                    line += 1
                out.append(text[j])
                j += 1
            else:
                j = n
            tokens.append(_Token("string", "".join(out), line))
            i = j
            continue

        if ch == '"':
            j = i + 1
            out = []
            while j < n:
                if text[j] == '"':
                    if j + 1 < n and text[j + 1] == '"':
                        out.append('"')
                        j += 2
                        continue
                    j += 1
                    break
                if text[j] == "\n":
                    line += 1
                out.append(text[j])
                j += 1
            else:
                j = n
            tokens.append(_Token("quoted", "".join(out), line))
            i = j
            continue

        if ch == "`":
            j = i + 1
            out = []
            while j < n:
                if text[j] == "`":
                    if j + 1 < n and text[j + 1] == "`":
                        out.append("`")
                        j += 2
                        continue
                    j += 1
                    break
                if text[j] == "\n":
                    line += 1
                out.append(text[j])
                j += 1
            else:
                j = n
            tokens.append(_Token("quoted", "".join(out), line))
            i = j
            continue

        if ch == "[":
            j = i + 1
            out = []
            while j < n and text[j] != "]":
                if text[j] == "\n":
                    line += 1
                out.append(text[j])
                j += 1
            if j < n:
                j += 1
            tokens.append(_Token("quoted", "".join(out), line))
            i = j
            continue

        if ch.isalnum() or ch in "_$":
            j = i
            while j < n and (text[j].isalnum() or text[j] in "_$"):
                j += 1
            tokens.append(_Token("identifier", text[i:j], line))
            i = j
            continue

        tokens.append(_Token("punct", ch, line))
        i += 1

    tokens.append(_Token("eof", "", line))
    return tokens


def _parse_qualified_name(tokens: list[_Token], i: int, line: int) -> tuple[str, int]:
    """Parse a possibly schema-qualified name and return the last component."""
    if i >= len(tokens) or not _is_name_token(tokens[i]):
        raise MapError("parse_error", f"parse error near line {line}")
    value = tokens[i].value
    i += 1
    while i < len(tokens) and tokens[i].kind == "punct" and tokens[i].value == ".":
        if i + 1 >= len(tokens) or not _is_name_token(tokens[i + 1]):
            raise MapError("parse_error", f"parse error near line {line}")
        value = tokens[i + 1].value
        i += 2
    return value, i


def _parse_reference_table_name(tokens: list[_Token], i: int, line: int) -> tuple[str, int]:
    """Parse a referenced table name, returning the last dotted component."""
    return _parse_qualified_name(tokens, i, line)


def _process_item(
    item_tokens: list[_Token],
    table_name: str,
    columns: list[str],
    references: list[tuple[str, str]],
    line: int,
) -> None:
    if not item_tokens:
        return

    # Table-level FOREIGN KEY ... REFERENCES t(col)
    foreign_idx: int | None = None
    for idx, tok in enumerate(item_tokens):
        if _is_keyword(tok, "FOREIGN"):
            foreign_idx = idx
            break

    if foreign_idx is not None:
        idx = foreign_idx
        if idx + 1 < len(item_tokens) and _is_keyword(item_tokens[idx + 1], "KEY"):
            idx += 1
        if idx + 1 >= len(item_tokens) or item_tokens[idx + 1].value != "(":
            raise MapError("parse_error", f"parse error near line {line}")
        idx += 2  # skip FOREIGN KEY (
        local_cols: list[str] = []
        depth = 1
        while idx < len(item_tokens):
            tok = item_tokens[idx]
            if tok.value == "(":
                depth += 1
                if depth > 32:
                    raise MapError("parse_error", f"parse error near line {line}")
            elif tok.value == ")":
                depth -= 1
                if depth == 0:
                    idx += 1
                    break
                idx += 1
                continue
            if _is_name_token(tok):
                local_cols.append(tok.value)
            idx += 1
        if idx >= len(item_tokens) or not _is_keyword(item_tokens[idx], "REFERENCES"):
            raise MapError("parse_error", f"parse error near line {line}")
        idx += 1
        ref_table, idx = _parse_reference_table_name(item_tokens, idx, line)
        for local_col in local_cols:
            references.append((local_col, ref_table))
        return

    if not item_tokens or not _is_name_token(item_tokens[0]):
        return

    first = item_tokens[0].value.upper()
    if first in {"CONSTRAINT", "PRIMARY", "UNIQUE", "CHECK", "KEY", "INDEX"}:
        return

    column_name = item_tokens[0].value
    columns.append(column_name)
    for idx in range(1, len(item_tokens)):
        if _is_keyword(item_tokens[idx], "REFERENCES"):
            if idx + 1 < len(item_tokens):
                ref_table, _ = _parse_reference_table_name(item_tokens, idx + 1, line)
                references.append((column_name, ref_table))
            break


def _parse_create_table(tokens: list[_Token], start: int) -> tuple[Table | None, int]:
    line = tokens[start].line
    i = start
    if not _is_keyword(tokens[i], "CREATE"):
        raise MapError("parse_error", f"parse error near line {line}")
    i += 1
    if i < len(tokens) and _is_keyword(tokens[i], "TEMPORARY"):
        i += 1
    if i >= len(tokens) or not _is_keyword(tokens[i], "TABLE"):
        raise MapError("parse_error", f"parse error near line {line}")
    i += 1

    if (
        i + 2 < len(tokens)
        and _is_keyword(tokens[i], "IF")
        and _is_keyword(tokens[i + 1], "NOT")
        and _is_keyword(tokens[i + 2], "EXISTS")
    ):
        i += 3

    table_name, i = _parse_qualified_name(tokens, i, line)
    if i >= len(tokens) or tokens[i].value != "(":
        # Not a column list (e.g. CREATE TABLE ... AS SELECT): skip it.
        while i < len(tokens) and tokens[i].kind != "eof" and tokens[i].value != ";":
            i += 1
        if i < len(tokens) and tokens[i].value == ";":
            i += 1
        return None, i
    i += 1  # consume opening parenthesis

    columns: list[str] = []
    references: list[tuple[str, str]] = []
    item_tokens: list[_Token] = []
    depth = 0

    while i < len(tokens):
        tok = tokens[i]
        if tok.kind == "eof":
            raise MapError("parse_error", f"parse error near line {line}")
        if tok.kind == "punct" and tok.value == "(":
            item_tokens.append(tok)
            depth += 1
            if depth > 32:
                raise MapError("parse_error", f"parse error near line {line}")
            i += 1
        elif tok.kind == "punct" and tok.value == ")":
            if depth == 0:
                if item_tokens:
                    _process_item(item_tokens, table_name, columns, references, line)
                i += 1
                break
            item_tokens.append(tok)
            depth -= 1
            i += 1
        elif tok.kind == "punct" and tok.value == "," and depth == 0:
            if item_tokens:
                _process_item(item_tokens, table_name, columns, references, line)
            item_tokens = []
            i += 1
        else:
            item_tokens.append(tok)
            i += 1
    else:
        raise MapError("parse_error", f"parse error near line {line}")

    # Skip optional suffixes (e.g., ENGINE=InnoDB) and the terminating semicolon.
    while i < len(tokens) and tokens[i].kind != "eof" and tokens[i].value != ";":
        i += 1
    if i < len(tokens) and tokens[i].value == ";":
        i += 1

    return Table(table_name, columns, references), i


def parse_ddl(
    text: str,
    *,
    max_bytes: int = 5_242_880,
    max_tables: int = 2000,
) -> list[Table]:
    """Parse DDL text and return the ``CREATE TABLE`` statements found.

    Raises:
        MapError: with code ``input_too_large``, ``parse_error``, or
            ``too_many_tables``.
    """
    if len(text.encode("utf-8")) > max_bytes:
        raise MapError("input_too_large")

    tokens = _tokenize(text)
    tables: list[Table] = []
    i = 0

    while i < len(tokens):
        tok = tokens[i]
        if tok.kind == "eof":
            break

        if _is_keyword(tok, "CREATE"):
            j = i
            if _is_keyword(tokens[j], "CREATE"):
                j += 1
            if j < len(tokens) and _is_keyword(tokens[j], "TEMPORARY"):
                j += 1
            if j < len(tokens) and _is_keyword(tokens[j], "TABLE"):
                table, new_i = _parse_create_table(tokens, i)
                if table is not None:
                    tables.append(table)
                    if len(tables) > max_tables:
                        raise MapError("too_many_tables")
                i = new_i
                continue

        while i < len(tokens) and tokens[i].kind != "eof" and tokens[i].value != ";":
            i += 1
        if i < len(tokens) and tokens[i].value == ";":
            i += 1

    return tables


def _tokenize_name(name: str) -> list[str]:
    """Split a name into lowercased tokens."""
    s = name.replace("_", " ").replace("-", " ")
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    return [part.lower() for part in re.split(r"\s+", s.strip()) if part]


def _contains_contiguous(column_tokens: list[str], phrase_tokens: list[str]) -> bool:
    if len(phrase_tokens) == 0:
        return False
    if len(phrase_tokens) > len(column_tokens):
        return False
    for start in range(len(column_tokens) - len(phrase_tokens) + 1):
        if tuple(column_tokens[start : start + len(phrase_tokens)]) == tuple(phrase_tokens):
            return True
    return False


def _match_rule(column_tokens: list[str], rule: Rule) -> bool:
    for phrase in rule.tokens:
        phrase_tokens = _tokenize_name(phrase)
        if _contains_contiguous(column_tokens, phrase_tokens):
            return True
    return False


def _validate_rules(rules: Sequence[Rule]) -> None:
    if not isinstance(rules, Sequence):
        raise MapError("invalid_rule")
    for rule in rules:
        try:
            category = rule.category
            tokens = rule.tokens
        except AttributeError:
            raise MapError("invalid_rule") from None
        if not isinstance(category, str) or not category:
            raise MapError("invalid_rule")
        if not isinstance(tokens, tuple) or not tokens:
            raise MapError("invalid_rule")
        for token in tokens:
            if not isinstance(token, str) or not token:
                raise MapError("invalid_rule")


def _shortest_path_to_subject(
    start: str,
    graph: dict[str, list[str]],
    subject_lowers: set[str],
    lower_to_original: dict[str, str],
) -> list[str] | None:
    dist: dict[str, int] = {start: 0}
    parent: dict[str, str | None] = {start: None}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nxt in graph.get(node, []):
            if nxt not in dist:
                dist[nxt] = dist[node] + 1
                parent[nxt] = node
                queue.append(nxt)

    candidates = [n for n in subject_lowers if n in dist]
    if not candidates:
        return None

    min_dist = min(dist[n] for n in candidates)
    candidates_at_dist = [n for n in candidates if dist[n] == min_dist]
    candidates_at_dist.sort(key=lambda n: lower_to_original.get(n, n))
    chosen = candidates_at_dist[0]

    path: list[str] = []
    walker: str = chosen
    while True:
        parent_node = parent.get(walker)
        if parent_node is None:
            break
        path.append(lower_to_original[walker])
        walker = parent_node
    path.reverse()
    return path


def classify(
    tables: Sequence[Table],
    *,
    rules: Sequence[Rule] = DEFAULT_RULES,
    overrides: Mapping[str, str | None] | None = None,
) -> DataMap:
    """Classify columns and compute roles for tables.

    Raises:
        MapError: with code ``invalid_override`` or ``invalid_rule``.
    """
    _validate_rules(rules)
    rules_tuple = tuple(rules)
    table_list = list(tables)
    lower_to_table = {t.name.lower(): t for t in table_list}

    categories = {rule.category for rule in rules_tuple}
    overrides_map: dict[tuple[str, str], str | None] = {}
    if overrides is not None:
        for key, value in overrides.items():
            if not isinstance(key, str) or key != key.lower():
                raise MapError("invalid_override")
            if key.count(".") != 1:
                raise MapError("invalid_override")
            table_lower, column_lower = key.split(".", 1)
            if not table_lower or not column_lower:
                raise MapError("invalid_override")
            table = lower_to_table.get(table_lower)
            if table is None:
                raise MapError("invalid_override")
            column_original = next((c for c in table.columns if c.lower() == column_lower), None)
            if column_original is None:
                raise MapError("invalid_override")
            if value is not None and (not isinstance(value, str) or value not in categories):
                raise MapError("invalid_override")
            overrides_map[(table.name, column_original)] = value

    columns_info: list[ColumnInfo] = []
    table_categories: dict[str, dict[str, str | None]] = {}
    for table in table_list:
        table_categories[table.name] = {}
        for col in table.columns:
            tokens = _tokenize_name(col)
            cat: str | None = None
            for rule in rules_tuple:
                if _match_rule(tokens, rule):
                    cat = rule.category
                    break
            override_key = (table.name, col)
            if override_key in overrides_map:
                cat = overrides_map[override_key]
            columns_info.append(ColumnInfo(table.name, col, cat))
            table_categories[table.name][col] = cat

    subject_lowers: set[str] = set()
    for table in table_list:
        if any(
            cat in {"direct_identifier", "name"} for cat in table_categories[table.name].values()
        ):
            subject_lowers.add(table.name.lower())

    lower_to_original = {t.name.lower(): t.name for t in table_list}
    graph: dict[str, list[str]] = {ln: [] for ln in lower_to_original}
    for table in table_list:
        for _, ref_table in table.references:
            ref_lower = ref_table.lower()
            if ref_lower in lower_to_original:
                graph[table.name.lower()].append(ref_lower)

    roles: dict[str, Role] = {}
    for table in table_list:
        table_lower = table.name.lower()
        if table_lower in subject_lowers:
            roles[table.name] = Role("subject", [])
        else:
            path = _shortest_path_to_subject(table_lower, graph, subject_lowers, lower_to_original)
            if path is not None:
                roles[table.name] = Role("linked", path)
            else:
                roles[table.name] = Role("none", [])

    special_category_tables: list[str] = []
    for table in table_list:
        if any(cat == "special_category" for cat in table_categories[table.name].values()):
            special_category_tables.append(table.name)

    return DataMap(columns_info, roles, special_category_tables)


def _table_order(data_map: DataMap) -> list[str]:
    seen: list[str] = []
    for ci in data_map.columns:
        if ci.table not in seen:
            seen.append(ci.table)
    return seen


def _escape_markdown(value: str) -> str:
    return value.replace("|", "\\|")


def render(data_map: DataMap, fmt: Literal["json", "markdown"]) -> str:
    """Render a DataMap as JSON or Markdown."""
    if fmt == "json":
        payload = {
            "columns": [
                {"table": ci.table, "column": ci.column, "category": ci.category}
                for ci in data_map.columns
            ],
            "roles": {
                table: {"role": role.role, "via": role.via}
                for table, role in data_map.roles.items()
            },
            "special_category_tables": data_map.special_category_tables,
        }
        return json.dumps(payload, sort_keys=True, indent=2)

    if fmt == "markdown":
        lines = [
            "| Table | Column | Category | Role |",
            "| --- | --- | --- | --- |",
        ]
        for table in _table_order(data_map):
            for ci in data_map.columns:
                if ci.table == table and ci.category is not None:
                    role = data_map.roles.get(table, Role("none", [])).role
                    lines.append(
                        f"| {_escape_markdown(ci.table)} | {_escape_markdown(ci.column)} "
                        f"| {_escape_markdown(ci.category)} | {role} |"
                    )
        return "\n".join(lines) + "\n"

    raise ValueError(f"unsupported format: {fmt}")
