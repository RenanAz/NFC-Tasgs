"""Config flow for NFC Tasgs integration."""

from __future__ import annotations

import json
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import selector

from .const import (
    CONF_ACTIONS,
    CONF_ACTION_INTERVAL,
    CONF_ACTION_KEY,
    CONF_ACTION_LABEL,
    CONF_ACTION_PURCHASE,
    CONF_ACTION_TASK,
    CONF_AREA_ID,
    CONF_ASSIGNEE,
    CONF_DEFAULT_ACTION,
    CONF_DOUBLE_SCAN_WINDOW,
    CONF_ICON,
    CONF_OWNERS,
    CONF_SHOPPING_LIST,
    CONF_TAG_ID,
    CONF_TASK_LIST,
    DEFAULT_DOUBLE_SCAN_WINDOW,
    DOMAIN,
)


class NfcTasgsConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_TAG_ID: user_input[CONF_TAG_ID],
                    CONF_DEFAULT_ACTION: user_input.get(CONF_DEFAULT_ACTION, "default"),
                    CONF_ACTIONS: _parse_actions_json(
                        user_input.get("actions_json", "")
                    ),
                    CONF_ICON: user_input.get(CONF_ICON, "mdi:clipboard-check"),
                    CONF_OWNERS: _parse_list(user_input.get("owners", "")),
                    CONF_AREA_ID: user_input.get(CONF_AREA_ID, ""),
                    CONF_ASSIGNEE: user_input.get(CONF_ASSIGNEE, ""),
                    CONF_DOUBLE_SCAN_WINDOW: user_input.get(
                        CONF_DOUBLE_SCAN_WINDOW, DEFAULT_DOUBLE_SCAN_WINDOW
                    ),
                },
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_TAG_ID): str,
                vol.Required(CONF_DEFAULT_ACTION, default="default"): str,
                vol.Optional("actions_json", default=""): str,
                vol.Optional(CONF_ICON, default="mdi:clipboard-check"): str,
                vol.Optional("owners", default=""): str,
                vol.Optional(CONF_AREA_ID, default=""): str,
                vol.Optional(CONF_ASSIGNEE, default=""): str,
                vol.Optional(
                    CONF_DOUBLE_SCAN_WINDOW, default=DEFAULT_DOUBLE_SCAN_WINDOW
                ): int,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "actions_help": 'JSON: [{"key":"cleaned","label":"Cleaned","expected_interval_hours":168,"triggers_purchase":false}]'
            },
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return NfcTasgsOptionsFlow(config_entry)


class NfcTasgsOptionsFlow(OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            actions = _parse_actions_json(user_input.get("actions_json", ""))
            if not actions:
                actions = self.config_entry.data.get(CONF_ACTIONS, [])
            return self.async_create_entry(
                data={
                    CONF_DEFAULT_ACTION: user_input.get(
                        CONF_DEFAULT_ACTION,
                        self.config_entry.data.get(CONF_DEFAULT_ACTION, "default"),
                    ),
                    CONF_ACTIONS: actions,
                    CONF_ICON: user_input.get(
                        CONF_ICON, self.config_entry.data.get(CONF_ICON, "")
                    ),
                    CONF_OWNERS: _parse_list(
                        user_input.get("owners", "")
                    ) or self.config_entry.data.get(CONF_OWNERS, []),
                    CONF_ASSIGNEE: user_input.get(
                        CONF_ASSIGNEE,
                        self.config_entry.data.get(CONF_ASSIGNEE, ""),
                    ),
                    CONF_DOUBLE_SCAN_WINDOW: user_input.get(
                        CONF_DOUBLE_SCAN_WINDOW,
                        self.config_entry.data.get(
                            CONF_DOUBLE_SCAN_WINDOW, DEFAULT_DOUBLE_SCAN_WINDOW
                        ),
                    ),
                    CONF_TASK_LIST: user_input.get(
                        CONF_TASK_LIST,
                        self.config_entry.data.get(CONF_TASK_LIST, ""),
                    ),
                    CONF_SHOPPING_LIST: user_input.get(
                        CONF_SHOPPING_LIST,
                        self.config_entry.data.get(CONF_SHOPPING_LIST, ""),
                    ),
                    CONF_AREA_ID: user_input.get(
                        CONF_AREA_ID,
                        self.config_entry.data.get(CONF_AREA_ID, ""),
                    ),
                }
            )

        current = self.config_entry.data
        actions_json = json.dumps(
            current.get(CONF_ACTIONS, []), indent=2, ensure_ascii=False
        )
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEFAULT_ACTION,
                    default=current.get(CONF_DEFAULT_ACTION, "default"),
                ): str,
                vol.Optional("actions_json", default=actions_json): str,
                vol.Optional(
                    CONF_ICON,
                    default=current.get(CONF_ICON, "mdi:clipboard-check"),
                ): str,
                vol.Optional(
                    "owners",
                    default=",".join(current.get(CONF_OWNERS, [])),
                ): str,
                vol.Optional(
                    CONF_ASSIGNEE,
                    default=current.get(CONF_ASSIGNEE, ""),
                ): str,
                vol.Optional(
                    CONF_DOUBLE_SCAN_WINDOW,
                    default=current.get(
                        CONF_DOUBLE_SCAN_WINDOW, DEFAULT_DOUBLE_SCAN_WINDOW
                    ),
                ): int,
                vol.Optional(
                    CONF_TASK_LIST,
                    default=current.get(CONF_TASK_LIST, ""),
                ): str,
                vol.Optional(
                    CONF_SHOPPING_LIST,
                    default=current.get(CONF_SHOPPING_LIST, ""),
                ): str,
                vol.Optional(
                    CONF_AREA_ID,
                    default=current.get(CONF_AREA_ID, ""),
                ): str,
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )


def _parse_actions_json(raw: str) -> list[dict]:
    if not raw or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            return []
        result = []
        for item in parsed:
            if isinstance(item, dict) and CONF_ACTION_KEY in item:
                result.append(
                    {
                        CONF_ACTION_KEY: item[CONF_ACTION_KEY],
                        CONF_ACTION_LABEL: item.get(
                            CONF_ACTION_LABEL, item[CONF_ACTION_KEY]
                        ),
                        CONF_ACTION_INTERVAL: item.get(CONF_ACTION_INTERVAL),
                        CONF_ACTION_PURCHASE: item.get(CONF_ACTION_PURCHASE, False),
                        CONF_ACTION_TASK: item.get(CONF_ACTION_TASK, False),
                    }
                )
        return result
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_list(raw: str) -> list[str]:
    if not raw or not raw.strip():
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]
