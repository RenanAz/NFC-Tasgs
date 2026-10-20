"""Catalog contract tests for appliance templates."""

from __future__ import annotations

from custom_components.nfc_tasgs.const import (
    CONF_ACTION_INTERVAL,
    CONF_ACTION_KEY,
    CONF_ACTION_LABEL,
    CONF_ACTION_PURCHASE,
    CONF_ACTION_QUICK,
    CONF_ACTION_TASK,
    CONF_ACTIONS,
)
from custom_components.nfc_tasgs.templates import (
    TEMPLATES,
    default_action_key,
    human_interval,
    recommended_action_keys,
    selected_actions,
    template_preview,
)
from custom_components.nfc_tasgs.util import derive_action_key, legacy_slugify, slugify


def test_template_ids_are_unique() -> None:
    ids = [template["id"] for template in TEMPLATES]
    assert len(ids) == len(set(ids))
    assert all(template["template_version"] == 1 for template in TEMPLATES)


def test_every_template_has_one_default_and_two_quick_actions() -> None:
    for template in TEMPLATES:
        actions = template[CONF_ACTIONS]
        defaults = [action for action in actions if action.get("default")]
        quick = [action for action in actions if action.get(CONF_ACTION_QUICK)]
        assert len(defaults) == 1, template["id"]
        assert len(quick) == 2, template["id"]
        assert defaults[0].get("recommended") is True
        assert all(action.get("recommended") for action in quick)
        assert defaults[0] not in quick


def test_template_action_keys_are_stable_slugs() -> None:
    for template in TEMPLATES:
        keys = [action[CONF_ACTION_KEY] for action in template[CONF_ACTIONS]]
        assert len(keys) == len(set(keys)), template["id"]
        for action in template[CONF_ACTIONS]:
            assert action[CONF_ACTION_KEY].replace("_", "").isalnum()
            assert action[CONF_ACTION_KEY].islower()
            assert action[CONF_ACTION_LABEL]
            assert action[CONF_ACTION_INTERVAL] > 0
            assert CONF_ACTION_PURCHASE not in action
            assert CONF_ACTION_TASK not in action


def test_default_and_recommended_helpers() -> None:
    for template in TEMPLATES:
        default = default_action_key(template)
        assert default in recommended_action_keys(template)


def test_human_interval() -> None:
    assert human_interval(24) == "every day"
    assert human_interval(96) == "every 4 days"
    assert human_interval(168) == "every week"
    assert human_interval(336) == "every 2 weeks"
    assert human_interval(2160) == "every 3 months"
    assert human_interval(None) == "no reminder"


def test_selected_actions_keep_catalog_order_and_drop_unselected() -> None:
    template = next(t for t in TEMPLATES if t["id"] == "coffee_machine")
    actions = selected_actions(template, ["beans_refilled", "cleaned"])
    assert [action[CONF_ACTION_KEY] for action in actions] == [
        "cleaned",
        "beans_refilled",
    ]
    assert actions[0][CONF_ACTION_LABEL] == "Cleaned"
    assert actions[0][CONF_ACTION_INTERVAL] == 168
    assert CONF_ACTION_QUICK in actions[1]


def test_slugify_matches_home_assistant_entity_ids() -> None:
    assert slugify("Café") == "cafe"
    assert slugify("Robô da Abby") == "robo_da_abby"
    assert slugify("Caixa da Fritas") == "caixa_da_fritas"


def test_legacy_slug_keeps_old_migration_prefix() -> None:
    assert legacy_slugify("Café") == "café"
    assert legacy_slugify("Caixa da Abby") == "caixa_da_abby"


def test_action_key_is_derived_from_label() -> None:
    assert derive_action_key("Beans Refilled") == "beans_refilled"
    assert derive_action_key("  Deep   Cleaned  ") == "deep_cleaned"
    assert derive_action_key("Filter-changed!") == "filter_changed"
    assert derive_action_key("Café cleaned") == "cafe_cleaned"
    assert derive_action_key("→") == "action"


def test_action_key_gets_a_unique_suffix() -> None:
    assert derive_action_key("Cleaned", {"cleaned"}) == "cleaned_2"
    assert derive_action_key("Cleaned", {"cleaned", "cleaned_2"}) == "cleaned_3"
    assert derive_action_key("Cleaned", {"other"}) == "cleaned"


def test_preview_uses_generated_entity_names() -> None:
    template = next(t for t in TEMPLATES if t["id"] == "litter_box")
    actions = selected_actions(template, ["cleaned", "litter_replaced"])
    preview = template_preview("Café", template, actions, "cleaned")
    assert "sensor.cafe_cleaned_*" in preview
    assert "binary_sensor.cafe_litter_replaced_overdue" in preview
    assert "button.cafe_log_cleaned" in preview
    assert "sensor.cafe_total_scans" in preview
    assert "Double-scan menu" in preview
