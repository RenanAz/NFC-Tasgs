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
