"""Button entities for NFC Tasgs integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ACTION_KEY,
    CONF_ACTION_LABEL,
    CONF_ACTIONS,
    CONF_DEFAULT_ACTION,
    DOMAIN,
    SERVICE_LOG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entry_data = hass.data[DOMAIN]["entries"][entry.entry_id]
    config = entry_data["config"]
    slug = entry_data["slug"]
    entities: list[ButtonEntity] = [NfcTasgsManualLogButton(entry_data, slug, config)]
    for action in config.get(CONF_ACTIONS, []):
        entities.append(
            NfcTasgsActionButton(entry_data, slug, config, action[CONF_ACTION_KEY])
        )
    async_add_entities(entities)


class _NfcTasgsBaseButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:gesture-tap-button"

    def __init__(self, entry_data: dict[str, Any], slug: str) -> None:
        self._entry_data = entry_data
        self._slug = slug
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_data["entry_id"])},
        }

    async def _log(self, action_key: str) -> None:
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_LOG,
            {
                "device_id": self._entry_data.get("device_id", ""),
                "action_key": action_key,
                "scanner": "Manual",
            },
            blocking=True,
        )


class NfcTasgsManualLogButton(_NfcTasgsBaseButton):
    """Log the default action without a tag."""

    def __init__(
        self,
        entry_data: dict[str, Any],
        slug: str,
        config: dict[str, Any],
    ) -> None:
        super().__init__(entry_data, slug)
        self._config = config
        self._attr_unique_id = f"{entry_data['entry_id']}_log_manual"
        self._attr_name = "Log manually"

    async def async_press(self) -> None:
        await self._log(self._config.get(CONF_DEFAULT_ACTION, "default"))


class NfcTasgsActionButton(_NfcTasgsBaseButton):
    """Log one specific action from the device page."""

    def __init__(
        self,
        entry_data: dict[str, Any],
        slug: str,
        config: dict[str, Any],
        action_key: str,
    ) -> None:
        super().__init__(entry_data, slug)
        self._action_key = action_key
        action_label = action_key
        for action in config.get(CONF_ACTIONS, []):
            if action[CONF_ACTION_KEY] == action_key:
                action_label = action.get(CONF_ACTION_LABEL, action_key)
                break
        self._attr_unique_id = f"{entry_data['entry_id']}_{action_key}_log"
        self._attr_name = f"Log {action_label}"
        self._attr_icon = "mdi:play-circle-outline"

    async def async_press(self) -> None:
        await self._log(self._action_key)
