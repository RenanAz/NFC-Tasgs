"""Curated appliance templates for the NFC Tasgs config flow.

The catalog is data-only on purpose: community templates can be reviewed and
tested without touching the flow or the entity platforms. Keys are part of the
public contract and must never be renamed once released.
"""

from __future__ import annotations

from typing import Any

from .const import (
    CONF_ACTION_INTERVAL,
    CONF_ACTION_KEY,
    CONF_ACTION_LABEL,
    CONF_ACTION_QUICK,
)
from .util import slugify

TEMPLATE_CUSTOM = "custom"

INTERVAL_LABELS = {
    24: "every day",
    48: "every 2 days",
    72: "every 3 days",
    96: "every 4 days",
    168: "every week",
    336: "every 2 weeks",
    720: "every month",
    1440: "every 2 months",
    2160: "every 3 months",
    4320: "every 6 months",
}


def _action(
    key: str,
    label: str,
    interval_hours: int,
    *,
    default: bool = False,
    recommended: bool = False,
    quick: bool = False,
    help_text: str | None = None,
) -> dict[str, Any]:
    return {
        CONF_ACTION_KEY: key,
        CONF_ACTION_LABEL: label,
        CONF_ACTION_INTERVAL: interval_hours,
        "default": default,
        "recommended": recommended,
        CONF_ACTION_QUICK: quick,
        "help": help_text,
    }


TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "id": "coffee_machine",
        "name": "Coffee Machine",
        "icon": "mdi:coffee",
        "category": "kitchen",
        "description": "Espresso or filter coffee machine",
        "actions": (
            _action("cleaned", "Cleaned", 168, default=True, recommended=True),
            _action(
                "beans_refilled",
                "Beans Refilled",
                96,
                recommended=True,
                quick=True,
            ),
            _action("descaled", "Descaled", 1440, recommended=True, quick=True),
            _action("filter_replaced", "Filter Replaced", 2160, recommended=True),
            _action("milk_system_cleaned", "Milk System Cleaned", 24),
            _action("water_tank_refilled", "Water Tank Refilled", 48),
        ),
    },
    {
        "id": "litter_box",
        "name": "Litter Box",
        "icon": "mdi:cat",
        "category": "pet",
        "description": "Manual or automatic cat litter box",
        "actions": (
            _action("cleaned", "Cleaned", 24, default=True, recommended=True),
            _action(
                "litter_replaced", "Litter Replaced", 720, recommended=True, quick=True
            ),
            _action("deep_cleaned", "Deep Cleaned", 336, recommended=True, quick=True),
            _action("carbon_filter_replaced", "Carbon Filter Replaced", 720),
            _action("liner_replaced", "Liner Replaced", 336),
            _action("drawer_emptied", "Drawer Emptied", 72),
        ),
    },
    {
        "id": "pet_feeder",
        "name": "Pet Feeder",
        "icon": "mdi:bowl-mix",
        "category": "pet",
        "description": "Automatic or gravity pet feeder",
        "actions": (
            _action("cleaned", "Cleaned", 168, default=True, recommended=True),
            _action("food_refilled", "Food Refilled", 48, recommended=True, quick=True),
            _action(
                "desiccant_replaced",
                "Desiccant Replaced",
                720,
                recommended=True,
                quick=True,
            ),
            _action("battery_replaced", "Battery Replaced", 2160),
        ),
    },
    {
        "id": "water_fountain",
        "name": "Water Fountain",
        "icon": "mdi:water",
        "category": "pet",
        "description": "Pet water fountain",
        "actions": (
            _action("cleaned", "Cleaned", 168, default=True, recommended=True),
            _action(
                "water_refilled", "Water Refilled", 48, recommended=True, quick=True
            ),
            _action(
                "filter_replaced", "Filter Replaced", 720, recommended=True, quick=True
            ),
            _action("pump_cleaned", "Pump Cleaned", 720),
        ),
    },
    {
        "id": "ac_unit",
        "name": "AC Unit",
        "icon": "mdi:air-conditioner",
        "category": "climate",
        "description": "Air conditioner cleaning and service",
        "actions": (
            _action(
                "cleaned",
                "Cleaned",
                720,
                default=True,
                recommended=True,
                help_text="Clean the filter and front grille.",
            ),
            _action(
                "filter_replaced",
                "Filter Replaced",
                4320,
                recommended=True,
                quick=True,
            ),
            _action("deep_cleaned", "Deep Cleaned", 4320, recommended=True, quick=True),
            _action("drain_line_flushed", "Drain Line Flushed", 4320),
            _action("coils_cleaned", "Coils Cleaned", 4320),
            _action("serviced", "Serviced", 4320),
        ),
    },
    {
        "id": "guinea_pig_habitat",
        "name": "Guinea Pig Habitat",
        "icon": "mdi:rabbit",
        "category": "small_pet",
        "description": "Guinea pig cage and habitat maintenance",
        "actions": (
            _action(
                "cleaned",
                "Cleaned",
                24,
                default=True,
                recommended=True,
                help_text="Spot-clean the habitat.",
            ),
            _action("hay_refilled", "Hay Refilled", 24, recommended=True, quick=True),
            _action("water_changed", "Water Changed", 24, recommended=True, quick=True),
            _action("bedding_replaced", "Bedding Replaced", 168, recommended=True),
            _action("deep_cleaned", "Deep Cleaned", 720),
            _action("nail_trimmed", "Nail Trimmed", 720),
        ),
    },
    {
        "id": "robot_vacuum",
        "name": "Robot Vacuum",
        "icon": "mdi:robot-vacuum",
        "category": "cleaning",
        "description": "Robot vacuum maintenance",
        "actions": (
            _action("maintained", "Maintained", 168, default=True, recommended=True),
            _action("bag_emptied", "Bag Emptied", 72, recommended=True, quick=True),
            _action(
                "filter_replaced", "Filter Replaced", 1440, recommended=True, quick=True
            ),
            _action("brush_replaced", "Brush Replaced", 2160, recommended=True),
            _action("mop_pad_cleaned", "Mop Pad Cleaned", 168),
            _action("sensors_wiped", "Sensors Wiped", 168),
        ),
    },
)

for _template in TEMPLATES:
    _template.setdefault("template_version", 1)

TEMPLATES_BY_ID = {template["id"]: template for template in TEMPLATES}


def get_template(template_id: str) -> dict[str, Any] | None:
    """Return a template by its stable ID."""
    return TEMPLATES_BY_ID.get(template_id)


def template_options() -> list[dict[str, str]]:
    """Options for the appliance picker."""
    options = [
        {"value": template["id"], "label": template["name"]} for template in TEMPLATES
    ]
    options.append(
        {"value": TEMPLATE_CUSTOM, "label": "Custom — choose actions yourself"}
    )
    return options


def human_interval(hours: int | float | None) -> str:
    """Render an interval without exposing developer units."""
    if hours is None:
        return "no reminder"
    if hours in INTERVAL_LABELS:
        return INTERVAL_LABELS[hours]
    if hours % 24 == 0:
        days = int(hours // 24)
        return f"every {days} days"
    return f"every {round(hours, 1)} hours"


def action_option_label(action: dict[str, Any]) -> str:
    """Checkbox label used by the template action picker."""
    return (
        f"{action[CONF_ACTION_LABEL]} — "
        f"{human_interval(action.get(CONF_ACTION_INTERVAL))}"
    )


def recommended_action_keys(template: dict[str, Any]) -> list[str]:
    return [
        action[CONF_ACTION_KEY]
        for action in template["actions"]
        if action.get("recommended")
    ]


def default_action_key(template: dict[str, Any]) -> str:
    for action in template["actions"]:
        if action.get("default"):
            return action[CONF_ACTION_KEY]
    return template["actions"][0][CONF_ACTION_KEY]


def selected_actions(
    template: dict[str, Any], selected_keys: list[str]
) -> list[dict[str, Any]]:
    """Build config-entry action dicts for the selected template actions."""
    chosen = set(selected_keys)
    actions: list[dict[str, Any]] = []
    for action in template["actions"]:
        key = action[CONF_ACTION_KEY]
        if key not in chosen:
            continue
        actions.append(
            {
                CONF_ACTION_KEY: key,
                CONF_ACTION_LABEL: action[CONF_ACTION_LABEL],
                CONF_ACTION_INTERVAL: action.get(CONF_ACTION_INTERVAL),
                CONF_ACTION_QUICK: bool(action.get(CONF_ACTION_QUICK)),
            }
        )
    return actions


def quick_action_labels(
    template: dict[str, Any], selected_keys: list[str]
) -> list[str]:
    """Labels for the two quick actions, in catalog order."""
    chosen = set(selected_keys)
    labels = [
        action[CONF_ACTION_LABEL]
        for action in template["actions"]
        if action.get(CONF_ACTION_QUICK) and action[CONF_ACTION_KEY] in chosen
    ]
    return labels[:2]


def template_preview(
    device_name: str,
    template: dict[str, Any],
    actions: list[dict[str, Any]],
    default_key: str,
) -> str:
    """Human-readable entity preview for the confirmation step."""
    slug = slugify(device_name)
    lines = ["**Selected actions**"]
    for action in actions:
        marker = " (default)" if action[CONF_ACTION_KEY] == default_key else ""
        lines.append(
            f"- {action[CONF_ACTION_LABEL]} — "
            f"{human_interval(action.get(CONF_ACTION_INTERVAL))}{marker}"
        )
    lines.append("")
    lines.append("**Entity pattern per selected action**")
    for action in actions:
        key = action[CONF_ACTION_KEY]
        lines.append(
            f"- {action[CONF_ACTION_LABEL]}: "
            f"`sensor.{slug}_{key}_*` · "
            f"`binary_sensor.{slug}_{key}_overdue` · "
            f"`button.{slug}_log_{key}`"
        )
    lines.append(
        f"- Device: `sensor.{slug}_total_scans`, `sensor.{slug}_last_scan`, "
        f"`sensor.{slug}_last_action`, `sensor.{slug}_last_scanner`"
    )
    quick = quick_action_labels(
        template, [action[CONF_ACTION_KEY] for action in actions]
    )
    quick.append("Open Appliance tasks")
    lines.append("")
    lines.append(f"**Double-scan menu:** {' · '.join(quick)}")
    return "\n".join(lines)
