"""Repository-level smoke tests.

These do not require Home Assistant and guard the integration's packaging
contract (manifest fields that CI and HACS depend on).
"""

from __future__ import annotations

import json
from pathlib import Path

MANIFEST = (
    Path(__file__).parents[1]
    / "custom_components"
    / "nfc_tasgs"
    / "manifest.json"
)


def test_manifest_is_valid_json() -> None:
    json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_domain() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["domain"] == "nfc_tasgs"


def test_manifest_has_version() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["version"]
