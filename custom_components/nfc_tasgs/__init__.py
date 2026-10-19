"""NFC Tasgs integration - track chores via NFC tag scans."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ACTION_KEY,
    ATTR_ACTION_LABEL,
    ATTR_ACTION_SCAN_COUNT,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_INTERVAL_HOURS,
    ATTR_MODE,
    ATTR_SCAN_COUNT,
    ATTR_SCANNER,
    ATTR_SCANNER_DEVICE_ID,
    ATTR_TIMESTAMP,
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
    EVENT_ACTION,
    PLATFORMS,
    SERVICE_LOG,
    SERVICE_RESET_ACTION,
    SERVICE_SCAN,
    SERVICE_SET_ASSIGNEE,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SIGNAL_UPDATE = f"{DOMAIN}_update"

STORAGE_DATA = dict[str, dict[str, Any]]


def signal_update(entry_id: str) -> str:
    """Dispatcher signal scoped to a single config entry."""
    return f"{SIGNAL_UPDATE}_{entry_id}"


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_").replace("'", "")


def _match_person(
    persons: list[tuple[str, list[str]]], tracker_ids: list[str]
) -> str | None:
    """Return the first person owning one of the tracker entity IDs."""
    wanted = set(tracker_ids)
    for name, trackers in persons:
        if wanted.intersection(trackers):
            return name
    return None


def _compute_interval(first_ts: float, last_ts: float, count: int) -> float | None:
    if count < 2:
        return None
    return (last_ts - first_ts) / 3600 / (count - 1)


def _compute_next_due(
    last_ts: float, interval_hours: float | None, seed_hours: float | None
) -> float | None:
    if interval_hours is not None:
        return last_ts + interval_hours * 3600
    if seed_hours is not None:
        if last_ts:
            return last_ts + seed_hours * 3600
        return datetime.now(UTC).timestamp() + seed_hours * 3600
    return None


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = Store[STORAGE_DATA](hass, STORAGE_VERSION, STORAGE_KEY)
    stored = await store.async_load()
    if stored is None:
        stored = {}

    if "store" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["store"] = store
    if "entries" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entries"] = {}

    config = _build_config(entry)
    dev_slug = _slugify(entry.data.get(CONF_NAME, entry.entry_id))
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_NAME, "NFC Tasg Device"),
        manufacturer="NFC Tasgs",
        model="Virtual Chore Device",
        suggested_area=config.get(CONF_AREA_ID),
    )

    history = stored.get(entry.entry_id, {})
    for action in config[CONF_ACTIONS]:
        key = action[CONF_ACTION_KEY]
        if key not in history:
            history[key] = {
                "first_scan_ts": 0.0,
                "last_scan_ts": 0.0,
                "total_scans": 0,
                "last_scanner": "",
                "last_scanner_device_id": "",
            }

    hass.data[DOMAIN]["entries"][entry.entry_id] = {
        "entry_id": entry.entry_id,
        "config": config,
        "history": history,
        "slug": dev_slug,
        "device_id": device_entry.id,
    }

    # Pre-import platform modules: HA's platform loader would otherwise import
    # them inside the event loop (see git history 0c24ac5).
    from . import binary_sensor as _binary_sensor  # noqa: F401
    from . import button as _button  # noqa: F401
    from . import sensor as _sensor  # noqa: F401

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.data[DOMAIN].get("services_registered"):
        _register_services(hass)
        hass.data[DOMAIN]["services_registered"] = True

    entry.async_on_unload(entry.add_update_listener(_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN]["entries"].pop(entry.entry_id, None)
    return unload_ok


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _build_config(entry: ConfigEntry) -> dict[str, Any]:
    data = dict(entry.data)
    data.update(entry.options)
    actions = data.get(CONF_ACTIONS, [])
    if not actions:
        default_key = data.get(CONF_DEFAULT_ACTION, "default")
        actions = [
            {CONF_ACTION_KEY: default_key, CONF_ACTION_LABEL: default_key.title()}
        ]
    for a in actions:
        a.setdefault(CONF_ACTION_INTERVAL, None)
        a.setdefault(CONF_ACTION_PURCHASE, False)
        a.setdefault(CONF_ACTION_TASK, False)
    data[CONF_ACTIONS] = actions
    data.setdefault(CONF_DOUBLE_SCAN_WINDOW, DEFAULT_DOUBLE_SCAN_WINDOW)
    data.setdefault(CONF_OWNERS, [])
    data.setdefault(CONF_ASSIGNEE, None)
    data.setdefault(CONF_TASK_LIST, None)
    data.setdefault(CONF_SHOPPING_LIST, None)
    data.setdefault(CONF_NOTIFY_ENTITY, None)
    data.setdefault(CONF_ICON, "mdi:clipboard-check")
    data.setdefault(CONF_AREA_ID, None)
    return data


def _get_entry_data(hass: HomeAssistant, call: ServiceCall) -> dict:
    """Find the config entry matching the service call's device target."""
    if call.data.get("device_id"):
        return _get_data_by_device(hass, call.data["device_id"])
    entry_id = _find_entry_by_device_target(hass, call)
    if entry_id is None:
        raise ServiceValidationError("No NFC Tasgs device targeted")
    return hass.data[DOMAIN]["entries"].get(entry_id, {})


def _get_data_by_device(hass: HomeAssistant, device_id: str) -> dict | None:
    for entry_data in hass.data[DOMAIN].get("entries", {}).values():
        if entry_data.get("device_id") == device_id:
            return entry_data
    return None


def _find_entry_by_device_target(hass: HomeAssistant, call: ServiceCall) -> str | None:
    targets = call.data.get("target") or call.data
    if "device_id" in targets:
        dev_id = targets["device_id"]
        for eid, ed in hass.data[DOMAIN].get("entries", {}).items():
            if ed.get("device_id") == dev_id:
                return eid
    return None


async def _save_history(hass: HomeAssistant) -> None:
    store: Store = hass.data[DOMAIN]["store"]
    data: dict[str, dict] = {}
    for entry_id, entry_data in hass.data[DOMAIN]["entries"].items():
        data[entry_id] = entry_data["history"]
    await store.async_save(data)


def _resolve_person(hass: HomeAssistant, scanner_device_id: str) -> tuple[str, str]:
    """Resolve scanner device ID to person name.

    Trackers are matched against the `device_trackers` attribute exposed by
    person states (covers YAML and storage persons). Person registry options
    are kept as a fallback for older setups that store them there.
    """
    ent_reg = async_get_entity_registry(hass)
    dev_reg = dr.async_get(hass)
    if dev_reg.async_get(scanner_device_id) is None:
        return "Unknown", scanner_device_id

    tracker_ids = [
        entity_entry.entity_id
        for entity_entry in ent_reg.entities.get_entries_for_device_id(
            scanner_device_id
        )
        if entity_entry.domain == "device_tracker"
    ]
    if not tracker_ids:
        return "Unknown", scanner_device_id

    person_from_state = _match_person(
        [
            (
                state.name or state.entity_id,
                list(state.attributes.get("device_trackers") or []),
            )
            for state in hass.states.async_all("person")
        ],
        tracker_ids,
    )
    if person_from_state:
        return person_from_state, scanner_device_id

    person_from_options = _match_person(
        [
            (
                person_entry.name
                or person_entry.original_name
                or person_entry.entity_id,
                list((person_entry.options or {}).get("device_trackers") or []),
            )
            for person_entry in ent_reg.entities.get_entries_for_domain("person")
        ],
        tracker_ids,
    )
    if person_from_options:
        return person_from_options, scanner_device_id

    return "Unknown", scanner_device_id


async def _handle_scan(hass: HomeAssistant, call: ServiceCall) -> None:
    tag_id = call.data["tag_id"]
    scanner_device_id = call.data["scanner_device_id"]
    action_key = call.data.get("action")

    entry_data = None
    for ed in hass.data[DOMAIN]["entries"].values():
        if ed["config"].get(CONF_TAG_ID) == tag_id:
            entry_data = ed
            break
    if entry_data is None:
        raise ServiceValidationError(f"No device found for tag {tag_id}")

    config = entry_data["config"]
    history = entry_data["history"]

    if not action_key:
        action_key = config[CONF_DEFAULT_ACTION]

    action_config = None
    for a in config[CONF_ACTIONS]:
        if a[CONF_ACTION_KEY] == action_key:
            action_config = a
            break
    if action_config is None:
        raise ServiceValidationError(
            f"Unknown action '{action_key}' for device '{config[CONF_NAME]}'"
        )

    person_name, _ = _resolve_person(hass, scanner_device_id)

    _record_scan(history, action_key, person_name, scanner_device_id)
    await _save_history(hass)
    _refresh_entities(hass, entry_data)
    _fire_event(
        hass,
        config,
        entry_data,
        action_key,
        action_config,
        person_name,
        scanner_device_id,
    )


async def _handle_log(hass: HomeAssistant, call: ServiceCall) -> None:
    entry_data = _get_entry_data(hass, call)
    if not entry_data:
        raise ServiceValidationError("No device targeted")

    action_key = call.data["action_key"]
    scanner = call.data.get("scanner", "Manual")

    config = entry_data["config"]
    history = entry_data["history"]

    action_config = None
    for a in config[CONF_ACTIONS]:
        if a[CONF_ACTION_KEY] == action_key:
            action_config = a
            break
    if action_config is None:
        raise ServiceValidationError(
            f"Unknown action '{action_key}' for device '{config[CONF_NAME]}'"
        )

    _record_scan(history, action_key, scanner, "")
    await _save_history(hass)
    _refresh_entities(hass, entry_data)
    _fire_event(hass, config, entry_data, action_key, action_config, scanner, "")


async def _handle_reset(hass: HomeAssistant, call: ServiceCall) -> None:
    entry_data = _get_entry_data(hass, call)
    if not entry_data:
        raise ServiceValidationError("No device targeted")
    action_key = call.data["action_key"]
    history = entry_data["history"]
    if action_key in history:
        history[action_key] = {
            "first_scan_ts": 0.0,
            "last_scan_ts": 0.0,
            "total_scans": 0,
            "last_scanner": "",
            "last_scanner_device_id": "",
        }
    await _save_history(hass)
    _refresh_entities(hass, entry_data)


async def _handle_set_assignee(hass: HomeAssistant, call: ServiceCall) -> None:
    entry_data = _get_entry_data(hass, call)
    if not entry_data:
        raise ServiceValidationError("No device targeted")
    person = call.data.get("person") or None
    entry = hass.config_entries.async_get_entry(entry_data["entry_id"])
    if entry is None:
        raise ServiceValidationError("Device entry not found")
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, CONF_ASSIGNEE: person},
        options={**entry.options, CONF_ASSIGNEE: person},
    )
    entry_data["config"][CONF_ASSIGNEE] = person


def _record_scan(
    history: dict, action_key: str, person: str, scanner_device_id: str
) -> None:
    now_ts = datetime.now(UTC).timestamp()
    if action_key not in history:
        history[action_key] = {
            "first_scan_ts": now_ts,
            "last_scan_ts": now_ts,
            "total_scans": 0,
            "last_scanner": "",
            "last_scanner_device_id": "",
        }
    rec = history[action_key]
    if rec["total_scans"] == 0:
        rec["first_scan_ts"] = now_ts
    rec["last_scan_ts"] = now_ts
    rec["total_scans"] += 1
    rec["last_scanner"] = person
    rec["last_scanner_device_id"] = scanner_device_id


def _fire_event(
    hass: HomeAssistant,
    config: dict,
    entry_data: dict,
    action_key: str,
    action_config: dict,
    person: str,
    scanner_device_id: str,
) -> None:
    history = entry_data["history"]
    rec = history.get(action_key, {})
    interval = _compute_interval(
        rec.get("first_scan_ts", 0),
        rec.get("last_scan_ts", 0),
        rec.get("total_scans", 1),
    )
    total_scans = sum(h.get("total_scans", 0) for h in history.values())
    hass.bus.async_fire(
        EVENT_ACTION,
        {
            ATTR_DEVICE_ID: entry_data["slug"],
            ATTR_DEVICE_NAME: config[CONF_NAME],
            ATTR_ACTION_KEY: action_key,
            ATTR_ACTION_LABEL: action_config.get(CONF_ACTION_LABEL, action_key),
            ATTR_SCANNER: person,
            ATTR_SCANNER_DEVICE_ID: scanner_device_id,
            ATTR_TIMESTAMP: datetime.now(UTC).isoformat(),
            ATTR_SCAN_COUNT: total_scans,
            ATTR_ACTION_SCAN_COUNT: rec.get("total_scans", 1),
            ATTR_MODE: "manual" if not scanner_device_id else "scan",
            ATTR_INTERVAL_HOURS: round(interval, 1) if interval else None,
        },
    )


def _refresh_entities(hass: HomeAssistant, entry_data: dict) -> None:
    """Trigger entity state updates for the affected entry only."""
    async_dispatcher_send(hass, signal_update(entry_data["entry_id"]))


def _register_services(hass: HomeAssistant) -> None:
    async def scan_service(call: ServiceCall) -> None:
        await _handle_scan(hass, call)

    async def log_service(call: ServiceCall) -> None:
        await _handle_log(hass, call)

    async def reset_service(call: ServiceCall) -> None:
        await _handle_reset(hass, call)

    async def assignee_service(call: ServiceCall) -> None:
        await _handle_set_assignee(hass, call)

    hass.services.async_register(DOMAIN, SERVICE_SCAN, scan_service)
    hass.services.async_register(DOMAIN, SERVICE_LOG, log_service)
    hass.services.async_register(DOMAIN, SERVICE_RESET_ACTION, reset_service)
    hass.services.async_register(DOMAIN, SERVICE_SET_ASSIGNEE, assignee_service)
