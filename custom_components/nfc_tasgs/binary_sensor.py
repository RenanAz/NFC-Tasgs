"""Binary sensor entities for NFC Tasgs integration."""

from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SIGNAL_UPDATE
from .const import (
    CONF_ACTION_INTERVAL,
    CONF_ACTION_KEY,
    CONF_ACTION_LABEL,
    CONF_ACTIONS,
    DOMAIN,
)
from . import _compute_interval, _compute_next_due


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

        self._attr_unique_id = f"{slug}_{action_key}_overdue"
        self._attr_name = f"{action_label} overdue"
        self._attr_icon = "mdi:alert-circle"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_data.get("device_id", slug))},
        }

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPDATE, self._handle_update
            )
        )

    @property
    def is_on(self) -> bool | None:
        history = self._entry_data.get("history", {})
        rec = history.get(self._action_key, {})
        last_ts = rec.get("last_scan_ts", 0)
        count = rec.get("total_scans", 0)

        if count == 0:
            return None

        interval = _compute_interval(
            rec.get("first_scan_ts", 0), last_ts, count
        )
        seed = None
        for a in self._config.get(CONF_ACTIONS, []):
            if a[CONF_ACTION_KEY] == self._action_key:
                seed = a.get(CONF_ACTION_INTERVAL)
                break

        due = _compute_next_due(last_ts, interval, seed)
        if due is None:
            if seed is not None and last_ts > 0:
                due = last_ts + seed * 3600
            else:
                return None

        return datetime.now(timezone.utc).timestamp() > due
