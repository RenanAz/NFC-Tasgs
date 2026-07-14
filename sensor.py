"""Sensor entities for NFC Tasgs integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import SIGNAL_UPDATE
from .const import (
    ACTION_SENSORS,
    CONF_ACTION_INTERVAL,
    CONF_ACTION_KEY,
    CONF_ACTION_LABEL,
    CONF_ACTIONS,
    DOMAIN,
)
from . import _compute_interval, _compute_next_due, _slugify


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    entry_data = hass.data[DOMAIN]["entries"][entry.entry_id]
    config = entry_data["config"]
    slug = entry_data["slug"]
    entities: list[SensorEntity] = []

    entities.append(
        NfcTasgsDeviceSensor(entry_data, "total_scans", slug, config, None)
    )
    entities.append(
        NfcTasgsDeviceSensor(entry_data, "last_scan", slug, config, None)
    )
    entities.append(
        NfcTasgsDeviceSensor(entry_data, "last_action", slug, config, None)
    )
    entities.append(
        NfcTasgsDeviceSensor(entry_data, "last_scanner", slug, config, None)
    )

    for action in config.get(CONF_ACTIONS, []):
        action_key = action[CONF_ACTION_KEY]
        for sensor_type in ACTION_SENSORS:
            entities.append(
                NfcTasgsActionSensor(
                    entry_data, sensor_type, slug, config, action_key
                )
            )

    async_add_entities(entities)


class NfcTasgsBaseSensor(SensorEntity):
    _attr_has_entity_name = True

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


class NfcTasgsDeviceSensor(NfcTasgsBaseSensor):
    def __init__(
        self,
        entry_data: dict,
        sensor_type: str,
        slug: str,
        config: dict,
        action_key: str | None,
    ) -> None:
        self._entry_data = entry_data
        self._sensor_type = sensor_type
        self._slug = slug
        self._config = config
        self._action_key = action_key
        self._attr_unique_id = f"{slug}_{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_data.get("device_id", slug))},
        }

        if sensor_type == "total_scans":
            self._attr_name = "Total scans"
            self._attr_icon = "mdi:counter"
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_native_unit_of_measurement = "scans"
        elif sensor_type == "last_scan":
            self._attr_name = "Last scan"
            self._attr_icon = "mdi:clock-outline"
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif sensor_type == "last_action":
            self._attr_name = "Last action"
            self._attr_icon = "mdi:list-status"
        elif sensor_type == "last_scanner":
            self._attr_name = "Last scanner"
            self._attr_icon = "mdi:account"

    @property
    def native_value(self) -> StateType:
        history = self._entry_data.get("history", {})
        if self._sensor_type == "total_scans":
            return sum(
                h.get("total_scans", 0) for h in history.values()
            )
        if self._sensor_type == "last_scan":
            latest = 0.0
            for h in history.values():
                ts = h.get("last_scan_ts", 0)
                if ts > latest:
                    latest = ts
            if latest == 0.0:
                return None
            return datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()
        if self._sensor_type == "last_action":
            latest_ts = 0.0
            latest_action = ""
            for key, h in history.items():
                ts = h.get("last_scan_ts", 0)
                if ts > latest_ts and h.get("total_scans", 0) > 0:
                    latest_ts = ts
                    for a in self._config.get(CONF_ACTIONS, []):
                        if a[CONF_ACTION_KEY] == key:
                            latest_action = a.get(CONF_ACTION_LABEL, key)
                            break
            return latest_action or None
        if self._sensor_type == "last_scanner":
            latest_ts = 0.0
            latest_scanner = ""
            for h in history.values():
                ts = h.get("last_scan_ts", 0)
                if ts > latest_ts and h.get("last_scanner"):
                    latest_ts = ts
                    latest_scanner = h["last_scanner"]
            return latest_scanner or None
        return None


class NfcTasgsActionSensor(NfcTasgsBaseSensor):
    def __init__(
        self,
        entry_data: dict,
        sensor_type: str,
        slug: str,
        config: dict,
        action_key: str,
    ) -> None:
        self._entry_data = entry_data
        self._sensor_type = sensor_type
        self._slug = slug
        self._config = config
        self._action_key = action_key
        self._attr_unique_id = f"{slug}_{action_key}_{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_data.get("device_id", slug))},
        }

        action_label = action_key
        for a in config.get(CONF_ACTIONS, []):
            if a[CONF_ACTION_KEY] == action_key:
                action_label = a.get(CONF_ACTION_LABEL, action_key)
                break

        if sensor_type == "last_scan":
            self._attr_name = f"{action_label} last scan"
            self._attr_icon = "mdi:clock-outline"
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif sensor_type == "interval_hours":
            self._attr_name = f"{action_label} interval"
            self._attr_icon = "mdi:timeline-clock"
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_native_unit_of_measurement = UnitOfTime.HOURS
        elif sensor_type == "next_due":
            self._attr_name = f"{action_label} next due"
            self._attr_icon = "mdi:calendar-clock"
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif sensor_type == "last_scanner":
            self._attr_name = f"{action_label} last scanner"
            self._attr_icon = "mdi:account"
        elif sensor_type == "total_scans":
            self._attr_name = f"{action_label} total scans"
            self._attr_icon = "mdi:counter"
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._attr_native_unit_of_measurement = "scans"

    @property
    def native_value(self) -> StateType:
        history = self._entry_data.get("history", {})
        rec = history.get(self._action_key, {})

        if self._sensor_type == "last_scan":
            ts = rec.get("last_scan_ts", 0)
            if not ts:
                return None
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

        if self._sensor_type == "interval_hours":
            count = rec.get("total_scans", 0)
            if count < 2:
                return None
            return round(
                _compute_interval(
                    rec.get("first_scan_ts", 0),
                    rec.get("last_scan_ts", 0),
                    count,
                ),
                1,
            )

        if self._sensor_type == "next_due":
            ts = rec.get("last_scan_ts", 0)
            count = rec.get("total_scans", 0)
            interval = _compute_interval(
                rec.get("first_scan_ts", 0), ts, count
            )
            seed = None
            for a in self._config.get(CONF_ACTIONS, []):
                if a[CONF_ACTION_KEY] == self._action_key:
                    seed = a.get(CONF_ACTION_INTERVAL)
                    break
            due = _compute_next_due(ts, interval, seed)
            if due is None:
                return None
            return datetime.fromtimestamp(due, tz=timezone.utc).isoformat()

        if self._sensor_type == "last_scanner":
            return rec.get("last_scanner") or None

        if self._sensor_type == "total_scans":
            return rec.get("total_scans", 0)

        return None
