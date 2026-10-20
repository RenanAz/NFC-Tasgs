"""Binary sensor entities for NFC Tasgs integration."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import _action_due, _defer_attributes, signal_update
from .const import (
    CONF_ACTION_KEY,
    CONF_ACTION_LABEL,
    CONF_ACTIONS,
    DOMAIN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entry_data = hass.data[DOMAIN]["entries"][entry.entry_id]
    config = entry_data["config"]
    slug = entry_data["slug"]
    entities: list[BinarySensorEntity] = []

    for action in config.get(CONF_ACTIONS, []):
        entities.append(
            NfcTasgsOverdueSensor(entry_data, slug, config, action[CONF_ACTION_KEY])
        )

    async_add_entities(entities)


class NfcTasgsOverdueSensor(BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        entry_data: dict,
        slug: str,
        config: dict,
        action_key: str,
    ) -> None:
        self._entry_data = entry_data
        self._slug = slug
        self._config = config
        self._action_key = action_key

        action_label = action_key
        for a in config.get(CONF_ACTIONS, []):
            if a[CONF_ACTION_KEY] == action_key:
                action_label = a.get(CONF_ACTION_LABEL, action_key)
                break

        self._attr_unique_id = f"{entry_data['entry_id']}_{action_key}_overdue"
        self._attr_name = f"{action_label} overdue"
        self._attr_icon = "mdi:alert-circle"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_data["entry_id"])},
        }

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                signal_update(self._entry_data["entry_id"]),
                self._handle_update,
            )
        )

    @property
    def is_on(self) -> bool | None:
        history = self._entry_data.get("history", {})
        rec = history.get(self._action_key, {})

        if rec.get("total_scans", 0) == 0:
            return None

        action = next(
            (
                item
                for item in self._config.get(CONF_ACTIONS, [])
                if item[CONF_ACTION_KEY] == self._action_key
            ),
            {},
        )
        due, _original = _action_due(rec, action)
        if due is None:
            return None

        return datetime.now(UTC).timestamp() > due

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        history = self._entry_data.get("history", {})
        rec = history.get(self._action_key, {})
        action = next(
            (
                item
                for item in self._config.get(CONF_ACTIONS, [])
                if item[CONF_ACTION_KEY] == self._action_key
            ),
            {},
        )
        effective, original = _action_due(rec, action)
        attrs = _defer_attributes(rec, effective, original)
        return attrs or None
