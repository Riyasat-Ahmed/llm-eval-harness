from __future__ import annotations

import re

CATEGORIES = ["Billing", "Technical issue", "Account access", "Shipping", "Refund", "Other"]

_NORMALIZED = {c.lower().replace(" ", ""): c for c in CATEGORIES}


def parse_label(raw: str) -> str | None:
    """Pull one of the known category labels out of raw model output.

    Returns None (an unparseable / unrecognized output) if no category matches,
    per F5: unparseable output counts as wrong and is flagged separately.
    """
    if not raw:
        return None

    text = raw.strip()
    # Strip common wrapping like quotes, trailing punctuation, markdown bullets.
    text = re.sub(r'^[\s"\'\-\*`]+|[\s"\'\.\*`]+$', "", text)

    key = text.lower().replace(" ", "").replace("_", "")
    if key in _NORMALIZED:
        return _NORMALIZED[key]

    # Fall back to searching for a known category name anywhere in the text,
    # e.g. a model that answers "Category: Billing" or a full sentence.
    lowered = text.lower()
    matches = [c for c in CATEGORIES if c.lower() in lowered]
    if len(matches) == 1:
        return matches[0]
    return None
