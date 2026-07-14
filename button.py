"""Button entities for NFC Tasgs integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
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
    async_add_entities([NfcTasgsManualLogButton(entry_data, slug, config)])


class NfcTasgsManualLogButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        entry_data: dict,
        slug: str,
        config: dict,
    ) -> None:
        self._entry_data = entry_data
        self._slug = slug
        self._config = config
        self._attr_unique_id = f"{slug}_log_manual"
        self._attr_name = "Log manually"
        self._attr_icon = "mdi:gesture-tap-button"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_data.get("device_id", slug))},
        }

    async def async_press(self) -> None:
        default_key = self._config.get(CONF_DEFAULT_ACTION, "default")
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_LOG,
            {
                "action_key": default_key,
                "scanner": "Manual",
            },
            target={"device_id": self._entry_data.get("device_id", "")},
            blocking=True,
        )
