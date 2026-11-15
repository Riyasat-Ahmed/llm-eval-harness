from __future__ import annotations


def exact_match(parsed: str | None, expected: str) -> bool:
    """F6: exact-match scorer for classification. An unparseable output (None)
    never counts as correct."""
    if parsed is None:
        return False
    return parsed.strip() == expected.strip()
