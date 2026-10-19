"""Regression tests for pure core logic.

The live instance exposes person trackers as `device_trackers` state
attributes; person registry options are empty. These tests pin the matching
logic so scans no longer silently resolve to "Unknown".
"""

from __future__ import annotations

from custom_components.nfc_tasgs import (
    _compute_next_due,
    _match_person,
    build_menu_actions,
    parse_menu_action,
    signal_update,
)
from custom_components.nfc_tasgs.const import MENU_ACTION_PREFIX

PERSONS = [
    ("Renan", ["device_tracker.pixel_9_pro_xl", "device_tracker.lenovo_tb_x606f"]),
    ("Michelle", ["device_tracker.iphone_14_mi"]),
    ("Nicole", ["device_tracker.nicole"]),
]

ACTIONS = [
    {"key": "cleaned", "label": "Cleaned"},
    {"key": "beans_refilled", "label": "Beans Refilled", "quick": True},
    {"key": "descaled", "label": "Descaled", "quick": True},
    {"key": "filter_replaced", "label": "Filter Replaced"},
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


def test_menu_skips_default_and_adds_gateway() -> None:
    buttons = build_menu_actions("token-1", ACTIONS, "cleaned", "device-1")
    assert [button["title"] for button in buttons] == [
        "Beans Refilled",
        "Descaled",
        "Open Appliance tasks",
    ]
    assert parse_menu_action(buttons[0]["action"]) == ("token-1", "beans_refilled")
    assert parse_menu_action(buttons[1]["action"]) == ("token-1", "descaled")
    assert buttons[2] == {
        "action": "URI",
        "title": "Open Appliance tasks",
        "uri": "/config/devices/device/device-1",
    }


def test_menu_falls_back_to_first_actions_without_quick_flags() -> None:
    buttons = build_menu_actions("token-1", ACTIONS[:2], "cleaned", "device-1")
    assert [button["title"] for button in buttons] == [
        "Beans Refilled",
        "Open Appliance tasks",
    ]


def test_parse_menu_action_rejects_foreign_actions() -> None:
    assert parse_menu_action("OPEN_DOOR") is None
    assert parse_menu_action("URI") is None
    assert parse_menu_action(f"{MENU_ACTION_PREFIX}no-separator") is None
    assert parse_menu_action(f"{MENU_ACTION_PREFIX}|cleaned") is None


def test_next_due_requires_a_scan_before_seed_applies() -> None:
    assert _compute_next_due(0, None, 24) is None
    assert _compute_next_due(1_000, None, 24) == 1_000 + 24 * 3600
    assert _compute_next_due(1_000, 2, 24) == 1_000 + 2 * 3600
