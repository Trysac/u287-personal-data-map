"""Behavior tests for the public API of personal_data_map."""

from __future__ import annotations

import pytest

import personal_data_map


def test_normalize_trims_and_lowercases() -> None:
    assert personal_data_map.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        personal_data_map.normalize(value)


def test_version_is_semver() -> None:
    parts = personal_data_map.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
