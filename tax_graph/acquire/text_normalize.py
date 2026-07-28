"""Shared source-text punctuation normalization.

Acquired source text must remain content-complete. The small replacement table
keeps the stored text ASCII without silently deleting source characters.
"""

from __future__ import annotations


PUNCTUATION_MAP = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2022": "-",
    "\xa0": " ",
}


def normalize_punctuation(value: str) -> str:
    """Map known source punctuation while preserving every other character."""
    return "".join(PUNCTUATION_MAP.get(character, character) for character in value)


def unmapped_non_ascii(value: str) -> tuple[str, ...]:
    """Return distinct non-ASCII characters that need an explicit mapping."""
    return tuple(sorted({character for character in value if ord(character) > 127 and character not in PUNCTUATION_MAP}))
