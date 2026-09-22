"""Guard every shipped Python module against syntax errors.

hassfest and the integration itself parse these files; a syntax error blocks
setup entirely (see PRD §8 and the `binary_sensor.py` incident). This test
needs no Home Assistant and runs in well under a second, so it fails fast.
"""

from __future__ import annotations

import ast
from pathlib import Path

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "nfc_tasgs"
SOURCES = sorted(INTEGRATION.rglob("*.py"))


def test_sources_are_present() -> None:
    assert SOURCES, f"no Python sources found under {INTEGRATION}"


def test_sources_parse() -> None:
    for path in SOURCES:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
