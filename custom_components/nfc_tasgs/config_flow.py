"""Config flow for NFC Tasgs integration."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    CONF_ACTION_INTERVAL,
    CONF_ACTION_KEY,
    CONF_ACTION_LABEL,
    CONF_ACTION_PURCHASE,
    CONF_ACTION_TASK,
    CONF_ACTIONS,
    CONF_AREA_ID,
    CONF_ASSIGNEE,
    CONF_DEFAULT_ACTION,
    CONF_DOUBLE_SCAN_WINDOW,
    CONF_ICON,
    CONF_NOTIFY_ENTITY,
    CONF_OWNERS,
    CONF_SHOPPING_LIST,
    CONF_TAG_ID,
    CONF_TASK_LIST,
    DEFAULT_DOUBLE_SCAN_WINDOW,
    DOMAIN,
)

ACTION_KEY_RE = re.compile(r"^[a-z0-9_]+$")

DEFAULT_ICON = "mdi:clipboard-check"


def _clean(value: Any) -> Any:
    """Normalize empty form values ('' / None) to None."""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class _ActionsEditorMixin:
    """Shared multi-step device + actions editor for config and options flows."""

    _actions: list[dict[str, Any]]
    _device: dict[str, Any]
    _editing_key: str | None
    _include_identity: bool

    def _init_state(self, data: dict[str, Any], *, include_identity: bool) -> None:
        self._device = dict(data)
        self._actions = [dict(action) for action in data.get(CONF_ACTIONS, [])]
        self._editing_key = None
        self._include_identity = include_identity

    # ------------------------------------------------------------- device
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._device.update(self._normalize_device(user_input))
            errors = self._validate_device()
            if not errors:
                return await self.async_step_actions()
            return self.async_show_form(
                step_id="user", data_schema=self._device_schema(), errors=errors
            )
        return self.async_show_form(step_id="user", data_schema=self._device_schema())

    def _validate_device(self) -> dict[str, str]:
        if not self._include_identity:
            return {}
        errors: dict[str, str] = {}
        if not self._device.get(CONF_NAME):
            errors[CONF_NAME] = "required"
        if not self._device.get(CONF_TAG_ID):
            errors[CONF_TAG_ID] = "required"
        return errors

    def _device_schema(self) -> vol.Schema:
        current = self._device
        fields: dict[Any, Any] = {}
        if self._include_identity:
            fields[vol.Required(CONF_NAME, default=current.get(CONF_NAME, ""))] = (
                selector({"text": {}})
            )
            fields[vol.Required(CONF_TAG_ID, default=current.get(CONF_TAG_ID, ""))] = (
                selector({"text": {}})
            )
        fields[
            vol.Optional(CONF_ICON, default=current.get(CONF_ICON) or DEFAULT_ICON)
        ] = selector({"icon": {}})
        fields[vol.Optional(CONF_AREA_ID, default=current.get(CONF_AREA_ID) or "")] = (
            selector({"area": {}})
        )
        fields[vol.Optional(CONF_OWNERS, default=current.get(CONF_OWNERS) or [])] = (
            selector({"entity": {"domain": "person", "multiple": True}})
        )
        fields[
            vol.Optional(CONF_ASSIGNEE, default=current.get(CONF_ASSIGNEE) or "")
        ] = selector({"entity": {"domain": "person"}})
        fields[
            vol.Optional(
                CONF_DOUBLE_SCAN_WINDOW,
                default=current.get(
                    CONF_DOUBLE_SCAN_WINDOW, DEFAULT_DOUBLE_SCAN_WINDOW
                ),
            )
        ] = selector(
            {
                "number": {
                    "min": 1,
                    "max": 30,
                    "step": 1,
                    "mode": "box",
                    "unit_of_measurement": "s",
                }
            }
        )
        fields[
            vol.Optional(
                CONF_NOTIFY_ENTITY, default=current.get(CONF_NOTIFY_ENTITY) or ""
            )
        ] = selector({"entity": {"domain": "notify"}})
        fields[
            vol.Optional(CONF_TASK_LIST, default=current.get(CONF_TASK_LIST) or "")
        ] = selector({"entity": {"domain": "todo"}})
        fields[
            vol.Optional(
                CONF_SHOPPING_LIST, default=current.get(CONF_SHOPPING_LIST) or ""
            )
        ] = selector({"entity": {"domain": "todo"}})
        return vol.Schema(fields)

    def _normalize_device(self, user_input: dict[str, Any]) -> dict[str, Any]:
        data = dict(user_input)
        for key in (
            CONF_NAME,
            CONF_TAG_ID,
            CONF_AREA_ID,
            CONF_ASSIGNEE,
            CONF_NOTIFY_ENTITY,
            CONF_TASK_LIST,
            CONF_SHOPPING_LIST,
            CONF_ICON,
        ):
            if key in data:
                data[key] = _clean(data[key])
        owners = data.get(CONF_OWNERS) or []
        if isinstance(owners, str):
            owners = [item.strip() for item in owners.split(",") if item.strip()]
        data[CONF_OWNERS] = owners
        data.setdefault(CONF_DOUBLE_SCAN_WINDOW, DEFAULT_DOUBLE_SCAN_WINDOW)
        return data

    # ------------------------------------------------------------ actions
    async def async_step_actions(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        menu = ["add_action"]
        if self._actions:
            menu.extend(["edit_action", "remove_action", "finish"])
        return self.async_show_menu(
            step_id="actions",
            menu_options=menu,
        )

    def _action_schema(self, defaults: dict[str, Any] | None = None) -> vol.Schema:
        current = defaults or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_ACTION_KEY, default=current.get(CONF_ACTION_KEY, "")
                ): selector({"text": {}}),
                vol.Required(
                    CONF_ACTION_LABEL, default=current.get(CONF_ACTION_LABEL, "")
                ): selector({"text": {}}),
                vol.Optional(
                    CONF_ACTION_INTERVAL,
                    default=current.get(CONF_ACTION_INTERVAL),
                ): selector(
                    {
                        "number": {
                            "min": 0,
                            "step": 1,
                            "mode": "box",
                            "unit_of_measurement": "h",
                        }
                    }
                ),
                vol.Optional(
                    CONF_ACTION_PURCHASE,
                    default=current.get(CONF_ACTION_PURCHASE, False),
                ): bool,
                vol.Optional(
                    CONF_ACTION_TASK, default=current.get(CONF_ACTION_TASK, False)
                ): bool,
            }
        )

    def _normalize_action(self, user_input: dict[str, Any]) -> dict[str, Any]:
        interval = _clean(user_input.get(CONF_ACTION_INTERVAL))
        return {
            CONF_ACTION_KEY: (user_input.get(CONF_ACTION_KEY) or "").strip().lower(),
            CONF_ACTION_LABEL: (
                _clean(user_input.get(CONF_ACTION_LABEL))
                or (user_input.get(CONF_ACTION_KEY) or "").strip()
            ),
            CONF_ACTION_INTERVAL: (
                float(interval) if interval not in (None, "") else None
            ),
            CONF_ACTION_PURCHASE: bool(user_input.get(CONF_ACTION_PURCHASE, False)),
            CONF_ACTION_TASK: bool(user_input.get(CONF_ACTION_TASK, False)),
        }

    def _validate_action(
        self, action: dict[str, Any], original_key: str | None = None
    ) -> dict[str, str]:
        errors: dict[str, str] = {}
        key = action[CONF_ACTION_KEY]
        if not ACTION_KEY_RE.fullmatch(key):
            errors[CONF_ACTION_KEY] = "invalid_key"
        elif any(
            existing[CONF_ACTION_KEY] == key and key != original_key
            for existing in self._actions
        ):
            errors[CONF_ACTION_KEY] = "duplicate_key"
        if not action[CONF_ACTION_LABEL]:
            errors[CONF_ACTION_LABEL] = "required"
        return errors

    async def async_step_add_action(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            action = self._normalize_action(user_input)
            errors = self._validate_action(action)
            if not errors:
                self._actions.append(action)
                return await self.async_step_actions()
        else:
            errors = {}
        return self.async_show_form(
            step_id="add_action",
            data_schema=self._action_schema(user_input),
            errors=errors or None,
        )

    async def async_step_edit_action(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._editing_key = user_input[CONF_ACTION_KEY]
            return await self.async_step_edit_action_form()
        return self.async_show_form(
            step_id="edit_action",
            data_schema=self._action_picker_schema(),
        )

    async def async_step_edit_action_form(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        original = next(
            (
                action
                for action in self._actions
                if action[CONF_ACTION_KEY] == self._editing_key
            ),
            None,
        )
        if original is None:
            return await self.async_step_actions()
        if user_input is not None:
            action = self._normalize_action(user_input)
            errors = self._validate_action(action, original_key=self._editing_key)
            if not errors:
                index = self._actions.index(original)
                self._actions[index] = action
                self._editing_key = None
                return await self.async_step_actions()
        else:
            action = original
            errors = {}
        return self.async_show_form(
            step_id="edit_action_form",
            data_schema=self._action_schema(action),
            errors=errors or None,
        )

    async def async_step_remove_action(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            key = user_input[CONF_ACTION_KEY]
            self._actions = [
                action for action in self._actions if action[CONF_ACTION_KEY] != key
            ]
            return await self.async_step_actions()
        return self.async_show_form(
            step_id="remove_action",
            data_schema=self._action_picker_schema(),
        )

    def _action_picker_schema(self) -> vol.Schema:
        options = [action[CONF_ACTION_KEY] for action in self._actions]
        return vol.Schema(
            {vol.Required(CONF_ACTION_KEY): selector({"select": {"options": options}})}
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        options = [action[CONF_ACTION_KEY] for action in self._actions]
        if not options:
            return await self.async_step_actions()
        default_key = self._device.get(CONF_DEFAULT_ACTION)
        if default_key not in options:
            default_key = options[0]
        if user_input is not None:
            return self._async_save(user_input[CONF_DEFAULT_ACTION])
        return self.async_show_form(
            step_id="finish",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEFAULT_ACTION, default=default_key): selector(
                        {"select": {"options": options}}
                    )
                }
            ),
        )

    def _async_save(self, default_key: str) -> ConfigFlowResult:
        raise NotImplementedError


class NfcTasgsConfigFlow(_ActionsEditorMixin, ConfigFlow, domain=DOMAIN):
    """Create a new tracked device."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if not hasattr(self, "_actions"):
            self._init_state({}, include_identity=True)
        if user_input is not None:
            tag_id = _clean(user_input.get(CONF_TAG_ID))
            if tag_id:
                self._async_abort_entries_match({CONF_TAG_ID: tag_id})
        return await super().async_step_user(user_input)

    def _async_save(self, default_key: str) -> ConfigFlowResult:
        return self.async_create_entry(
            title=self._device[CONF_NAME],
            data={
                **self._device,
                CONF_DEFAULT_ACTION: default_key,
                CONF_ACTIONS: list(self._actions),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NfcTasgsOptionsFlow:
        """Return the options flow."""
        return NfcTasgsOptionsFlow()


class NfcTasgsOptionsFlow(_ActionsEditorMixin, OptionsFlow):
    """Edit an existing tracked device."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if not hasattr(self, "_actions"):
            data = dict(self.config_entry.data)
            data.update(self.config_entry.options)
            self._init_state(data, include_identity=False)
        return await self.async_step_user(user_input)

    def _async_save(self, default_key: str) -> ConfigFlowResult:
        return self.async_create_entry(
            data={
                **self._device,
                CONF_DEFAULT_ACTION: default_key,
                CONF_ACTIONS: list(self._actions),
            },
        )
