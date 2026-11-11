"""Tests for the public API of personal_data_map."""

from __future__ import annotations

import json

import pytest

from personal_data_map import (
    DEFAULT_RULES,
    ColumnInfo,
    MapError,
    Role,
    Rule,
    Table,
    classify,
    parse_ddl,
    render,
)
from personal_data_map.__main__ import main


def test_parse_simple() -> None:
    ddl = "CREATE TABLE users (id INT PRIMARY KEY, email VARCHAR(255) NOT NULL, created_at TIMESTAMP);"
    assert parse_ddl(ddl) == [
        Table(
            name="users",
            columns=["id", "email", "created_at"],
            references=[],
        )
    ]


def test_classify_basic() -> None:
    ddl = (
        "CREATE TABLE users (id INT PRIMARY KEY, "
        "email VARCHAR(255) NOT NULL, created_at TIMESTAMP);"
    )
    tables = parse_ddl(ddl)
    dm = classify(tables)
    assert dm.columns == [
        ColumnInfo("users", "id", None),
        ColumnInfo("users", "email", "direct_identifier"),
        ColumnInfo("users", "created_at", None),
    ]
    assert dm.roles == {"users": Role("subject", [])}
    assert dm.special_category_tables == []


def test_classify_linked_roles() -> None:
    ddl = """
    CREATE TABLE users (id INT PRIMARY KEY, email VARCHAR(255));
    CREATE TABLE orders (id INT, user_id INT REFERENCES users(id), total NUMERIC);
    CREATE TABLE audit (id INT, order_id INT, FOREIGN KEY (order_id) REFERENCES orders(id));
    """
    tables = parse_ddl(ddl)
    dm = classify(tables)
    assert dm.roles == {
        "users": Role("subject", []),
        "orders": Role("linked", ["users"]),
        "audit": Role("linked", ["orders", "users"]),
    }


def test_name_token_matching_boundaries() -> None:
    ddl = """
    CREATE TABLE t (
        emailed_at VARCHAR,
        ship_date DATE,
        latency_ms INT,
        zipped_size INT,
        billingEmail VARCHAR,
        home_zip_code VARCHAR,
        client_ip VARCHAR
    );
    """
    tables = parse_ddl(ddl)
    dm = classify(tables)
    by_col = {ci.column: ci.category for ci in dm.columns}
    assert by_col["emailed_at"] is None
    assert by_col["ship_date"] is None
    assert by_col["latency_ms"] is None
    assert by_col["zipped_size"] is None
    assert by_col["billingEmail"] == "direct_identifier"
    assert by_col["home_zip_code"] == "contact_address"
    assert by_col["client_ip"] == "online_identifier"


def test_special_category_table() -> None:
    ddl = "CREATE TABLE patients (id INT, diagnosis_code VARCHAR);"
    tables = parse_ddl(ddl)
    dm = classify(tables)
    assert dm.columns[1].category == "special_category"
    assert dm.special_category_tables == ["patients"]


def test_quoted_names_comments_and_string_with_close_paren() -> None:
    ddl = """
    CREATE TABLE "User Profiles" (
        `last_name` VARCHAR,
        -- email INT,
        note VARCHAR DEFAULT ')',
        [full name] VARCHAR
    );
    INSERT INTO other VALUES (1);
    """
    tables = parse_ddl(ddl)
    assert len(tables) == 1
    table = tables[0]
    assert table.name == "User Profiles"
    assert table.columns == ["last_name", "note", "full name"]


def test_overrides_and_errors() -> None:
    ddl = "CREATE TABLE users (id INT, email VARCHAR);"
    tables = parse_ddl(ddl)
    dm = classify(tables)
    assert dm.columns[1].category == "direct_identifier"
    dm2 = classify(tables, overrides={"users.email": None})
    assert dm2.columns[1].category is None
    with pytest.raises(MapError) as exc_info:
        classify(tables, overrides={"users.email": "secret"})
    assert exc_info.value.code == "invalid_override"


def test_input_too_large() -> None:
    # 5_242_881 bytes is one byte over the default maximum.
    text = "x" * 5_242_881
    with pytest.raises(MapError) as exc_info:
        parse_ddl(text)
    assert exc_info.value.code == "input_too_large"


def test_parse_error_unterminated() -> None:
    with pytest.raises(MapError) as exc_info:
        parse_ddl("CREATE TABLE t (a INT")
    assert exc_info.value.code == "parse_error"
    assert "line 1" in exc_info.value.message


def test_parenthesis_depth_limit() -> None:
    ddl = "CREATE TABLE t (a DECIMAL" + "(" * 33 + ")" * 33 + ");"
    with pytest.raises(MapError) as exc_info:
        parse_ddl(ddl)
    assert exc_info.value.code == "parse_error"


def test_too_many_tables() -> None:
    ddl = "CREATE TABLE a (x INT); CREATE TABLE b (y INT);"
    with pytest.raises(MapError) as exc_info:
        parse_ddl(ddl, max_tables=1)
    assert exc_info.value.code == "too_many_tables"


def test_render_markdown_exact() -> None:
    ddl = (
        "CREATE TABLE users (id INT PRIMARY KEY, "
        "email VARCHAR(255) NOT NULL, created_at TIMESTAMP);"
    )
    tables = parse_ddl(ddl)
    dm = classify(tables)
    expected = "| Table | Column | Category | Role |\n| --- | --- | --- | --- |\n| users | email | direct_identifier | subject |\n"
    assert render(dm, "markdown") == expected


def test_render_json_sorted_keys() -> None:
    ddl = "CREATE TABLE users (id INT, email VARCHAR);"
    tables = parse_ddl(ddl)
    dm = classify(tables)
    rendered = render(dm, "json")
    payload = json.loads(rendered)
    assert list(payload.keys()) == [
        "columns",
        "roles",
        "special_category_tables",
    ]
    assert '\n  "columns"' in rendered  # check indentation is 2 spaces


def test_cli_success_and_fail_on(tmp_path: pytest.TempPathFactory) -> None:
    schema = tmp_path / "schema.sql"
    schema.write_text(
        "CREATE TABLE users (id INT, email VARCHAR);\n"
        "CREATE TABLE patients (id INT, diagnosis_code VARCHAR);\n",
        encoding="utf-8",
    )
    assert main([str(schema)]) == 0
    assert main([str(schema), "--fail-on", "special_category"]) == 1
    assert main([str(schema), "--fail-on", "direct_identifier"]) == 1
    assert main([str(schema), "--fail-on", "nonexistent"]) == 0


def test_cli_usage_and_io_errors(tmp_path: pytest.TempPathFactory) -> None:
    assert main([]) == 2
    missing = tmp_path / "missing.sql"
    assert main([str(missing)]) == 2


def test_reference_cycle_and_self_reference() -> None:
    ddl = """
    CREATE TABLE a (id INT, b_id INT REFERENCES b(id));
    CREATE TABLE b (id INT, a_id INT REFERENCES a(id), self_id INT REFERENCES b(id));
    """
    tables = parse_ddl(ddl)
    dm = classify(tables)
    assert dm.roles["a"].role == "none"
    assert dm.roles["b"].role == "none"


def test_schema_qualified_name() -> None:
    ddl = "CREATE TABLE public.users (id INT);"
    tables = parse_ddl(ddl)
    assert tables[0].name == "users"


def test_create_table_as_select_skipped() -> None:
    ddl = "CREATE TABLE foo AS SELECT * FROM bar; CREATE TABLE baz (id INT);"
    tables = parse_ddl(ddl)
    assert [t.name for t in tables] == ["baz"]


def test_mysql_engine_suffix() -> None:
    ddl = "CREATE TABLE t (id INT PRIMARY KEY, email VARCHAR) ENGINE=InnoDB;"
    tables = parse_ddl(ddl)
    assert tables[0].columns == ["id", "email"]


def test_invalid_rule() -> None:
    ddl = "CREATE TABLE users (id INT, email VARCHAR);"
    tables = parse_ddl(ddl)
    bad_rule = Rule("", ("email",))
    with pytest.raises(MapError) as exc_info:
        classify(tables, rules=(bad_rule,))
    assert exc_info.value.code == "invalid_rule"


def test_default_rules_structure() -> None:
    assert isinstance(DEFAULT_RULES, tuple)
    assert all(isinstance(r, Rule) for r in DEFAULT_RULES)
    assert [r.category for r in DEFAULT_RULES] == [
        "special_category",
        "direct_identifier",
        "name",
        "date_of_birth",
        "contact_address",
        "online_identifier",
        "financial",
        "location",
    ]
