"""Small shared helpers for NFC Tasgs."""

from __future__ import annotations

import re
import unicodedata


def slugify(name: str) -> str:
    """Match Home Assistant's entity-id slug style, including accents."""
    value = unicodedata.normalize("NFKD", name)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def legacy_slugify(name: str) -> str:
    """The pre-template slug format, kept for unique-ID migration."""
    return name.lower().replace(" ", "_").replace("-", "_").replace("'", "")


def derive_action_key(label: str, existing_keys: set[str] | None = None) -> str:
    """Turn a human label into a valid, unique action key.

    Uppercase and accents are folded, spaces/punctuation become underscores,
    and a numeric suffix is added if the key is already in use.
    """
    used = existing_keys or set()
    base = slugify(label) or "action"
    if base not in used:
        return base
    index = 2
    while f"{base}_{index}" in used:
        index += 1
    return f"{base}_{index}"
