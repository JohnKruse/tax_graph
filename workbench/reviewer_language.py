"""Shared validation rules for reviewer-facing language."""

from __future__ import annotations

import re


RAW_FIELD_NAME = re.compile(r"^(?:[fc]\d+_\d+|.+\[(?:\d+)\])$")
RAW_FIELD_NAME_TOKEN = re.compile(r"(?<![A-Za-z0-9_])[fc]\d+_\d+(?![A-Za-z0-9_])")


def is_raw_field_name(value: str) -> bool:
    """Return whether *value* looks like an internal AcroForm field name."""
    return bool(RAW_FIELD_NAME.fullmatch(value.strip()))


def contains_raw_field_name_token(value: str) -> bool:
    """Return whether reviewer-facing text embeds an AcroForm leaf token."""
    return bool(RAW_FIELD_NAME_TOKEN.search(value))
