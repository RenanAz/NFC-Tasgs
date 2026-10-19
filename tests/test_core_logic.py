"""Regression tests for pure core logic.

The live instance exposes person trackers as `device_trackers` state
attributes; person registry options are empty. These tests pin the matching
logic so scans no longer silently resolve to "Unknown".
"""

from __future__ import annotations

from custom_components.nfc_tasgs import _match_person, signal_update

PERSONS = [
    ("Renan", ["device_tracker.pixel_9_pro_xl", "device_tracker.lenovo_tb_x606f"]),
    ("Michelle", ["device_tracker.iphone_14_mi"]),
    ("Nicole", ["device_tracker.nicole"]),
]


def test_signal_is_scoped_per_entry() -> None:
    assert signal_update("entry-a") != signal_update("entry-b")
    assert signal_update("entry-a").startswith("nfc_tasgs_update_")


def test_match_person_by_state_trackers() -> None:
    assert _match_person(PERSONS, ["device_tracker.pixel_9_pro_xl"]) == "Renan"
    assert _match_person(PERSONS, ["device_tracker.iphone_14_mi"]) == "Michelle"
    assert _match_person(PERSONS, ["device_tracker.nicole"]) == "Nicole"


def test_match_person_returns_none_without_match() -> None:
    assert _match_person(PERSONS, ["device_tracker.unknown"]) is None
    assert _match_person(PERSONS, []) is None
