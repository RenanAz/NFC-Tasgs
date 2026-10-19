"""NFC Tasgs integration - track chores via NFC tag scans."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Any
from uuid import uuid4

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.event import async_call_later, async_track_time_interval
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
    CONF_AUTO_SCAN,
    CONF_DEFAULT_ACTION,
    CONF_DOUBLE_SCAN_WINDOW,
    CONF_ICON,
    CONF_NOTIFY_SERVICE,
    CONF_OWNERS,
    CONF_SHOPPING_LIST,
    CONF_TAG_ID,
    CONF_TASK_LIST,
    DEFAULT_DOUBLE_SCAN_WINDOW,
    DOMAIN,
    EVENT_ACTION,
    EVENT_NOTIFICATION_ACTION,
    EVENT_OVERDUE,
    MENU_ACTION_PREFIX,
    MENU_TTL_SECONDS,
    OVERDUE_NOTIFY_COOLDOWN_HOURS,
    PLATFORMS,
    SERVICE_CHECK_OVERDUE,
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
    if seed_hours is not None and last_ts:
        return last_ts + seed_hours * 3600
    return None


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("pending", {})
    hass.data[DOMAIN].setdefault("menus", {})
    if not hass.data[DOMAIN].get("overdue_scheduled"):
        async_track_time_interval(
            hass,
            partial(_async_check_overdue, hass),
            timedelta(hours=1),
        )
        hass.data[DOMAIN]["overdue_scheduled"] = True
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
    hass.data[DOMAIN].setdefault("pending", {})
    hass.data[DOMAIN].setdefault("menus", {})

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
                "last_overdue_notify_ts": 0.0,
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
    data.setdefault(CONF_AUTO_SCAN, True)
    data.setdefault(CONF_OWNERS, [])
    data.setdefault(CONF_ASSIGNEE, None)
    data.setdefault(CONF_TASK_LIST, None)
    data.setdefault(CONF_SHOPPING_LIST, None)
    data.setdefault(CONF_NOTIFY_SERVICE, None)
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


def _find_entry_by_tag(hass: HomeAssistant, tag_id: str) -> dict | None:
    """Return the entry data for a tag, if configured."""
    for entry_data in hass.data[DOMAIN].get("entries", {}).values():
        if entry_data["config"].get(CONF_TAG_ID) == tag_id:
            return entry_data
    return None


async def _log_action(
    hass: HomeAssistant,
    entry_data: dict,
    action_key: str,
    person: str,
    scanner_device_id: str,
) -> None:
    """Record an action and refresh its entities."""
    config = entry_data["config"]
    action_config = next(
        (
            action
            for action in config[CONF_ACTIONS]
            if action[CONF_ACTION_KEY] == action_key
        ),
        None,
    )
    if action_config is None:
        raise ServiceValidationError(
            f"Unknown action '{action_key}' for device '{config[CONF_NAME]}'"
        )

    _record_scan(entry_data["history"], action_key, person, scanner_device_id)
    await _save_history(hass)
    _refresh_entities(hass, entry_data)

    if action_config.get(CONF_ACTION_PURCHASE):
        await _add_shopping_item(hass, entry_data, action_config)
    if action_config.get(CONF_ACTION_TASK):
        await _complete_task(hass, entry_data, action_config)

    _fire_event(
        hass,
        config,
        entry_data,
        action_key,
        action_config,
        person,
        scanner_device_id,
    )


def _action_item_summary(entry_data: dict, action_config: dict) -> str:
    label = action_config.get(CONF_ACTION_LABEL, action_config[CONF_ACTION_KEY])
    return f"{label} ({entry_data['config'].get(CONF_NAME)})"


async def _get_todo_items(hass: HomeAssistant, entity_id: str) -> list[dict]:
    response = await hass.services.async_call(
        "todo",
        "get_items",
        {"entity_id": entity_id},
        blocking=True,
        return_response=True,
    )
    return (response.get(entity_id) or {}).get("items", [])


async def _add_shopping_item(
    hass: HomeAssistant, entry_data: dict, action_config: dict
) -> None:
    entity_id = entry_data["config"].get(CONF_SHOPPING_LIST)
    if not entity_id:
        return
    summary = _action_item_summary(entry_data, action_config)
    try:
        items = await _get_todo_items(hass, entity_id)
        if any(
            item.get("summary") == summary and item.get("status") == "needs_action"
            for item in items
        ):
            return
        await hass.services.async_call(
            "todo",
            "add_item",
            {"entity_id": entity_id, "item": summary},
            blocking=True,
        )
    except HomeAssistantError as err:
        _LOGGER.warning("Could not add shopping item '%s': %s", summary, err)


async def _complete_task(
    hass: HomeAssistant, entry_data: dict, action_config: dict
) -> None:
    entity_id = entry_data["config"].get(CONF_TASK_LIST)
    if not entity_id:
        return
    summary = _action_item_summary(entry_data, action_config)
    try:
        items = await _get_todo_items(hass, entity_id)
        match = next(
            (
                item
                for item in items
                if item.get("summary") == summary
                and item.get("status") == "needs_action"
            ),
            None,
        )
        if match is None:
            return
        await hass.services.async_call(
            "todo",
            "update_item",
            {
                "entity_id": entity_id,
                "item": match.get("uid") or summary,
                "status": "completed",
            },
            blocking=True,
        )
    except HomeAssistantError as err:
        _LOGGER.warning("Could not complete task '%s': %s", summary, err)


async def _process_scan(
    hass: HomeAssistant,
    tag_id: str,
    scanner_device_id: str,
    action_key: str | None = None,
) -> None:
    """Resolve a scanned tag and either log or open the action menu."""
    entry_data = _find_entry_by_tag(hass, tag_id)
    if entry_data is None:
        raise ServiceValidationError(f"No device found for tag {tag_id}")

    person_name, _ = _resolve_person(hass, scanner_device_id)

    if action_key:
        await _log_action(hass, entry_data, action_key, person_name, scanner_device_id)
        return

    await _start_scan_window(hass, entry_data, tag_id, scanner_device_id, person_name)


async def _handle_scan(hass: HomeAssistant, call: ServiceCall) -> None:
    await _process_scan(
        hass,
        call.data["tag_id"],
        call.data["scanner_device_id"],
        call.data.get("action"),
    )


@callback
def _handle_tag_scanned(hass: HomeAssistant, event: Any) -> None:
    """Handle the companion app's tag_scanned event automatically."""
    tag_id = event.data.get("tag_id")
    if not tag_id:
        return
    entry_data = _find_entry_by_tag(hass, tag_id)
    if entry_data is None or not entry_data["config"].get(CONF_AUTO_SCAN, True):
        return
    hass.async_create_task(
        _process_scan(
            hass,
            tag_id,
            event.data.get("device_id", ""),
            None,
        )
    )


async def _start_scan_window(
    hass: HomeAssistant,
    entry_data: dict,
    tag_id: str,
    scanner_device_id: str,
    person_name: str,
) -> None:
    """Log on a single scan, or open the action menu on a double scan."""
    pending = hass.data[DOMAIN]["pending"].pop(tag_id, None)
    if pending is not None:
        pending["cancel"]()
        await _send_action_menu(hass, entry_data, scanner_device_id, person_name)
        return

    entry_id = entry_data["entry_id"]
    window = entry_data["config"].get(
        CONF_DOUBLE_SCAN_WINDOW, DEFAULT_DOUBLE_SCAN_WINDOW
    )

    @callback
    def _commit(_now: datetime) -> None:
        hass.data[DOMAIN]["pending"].pop(tag_id, None)
        current = hass.data[DOMAIN]["entries"].get(entry_id)
        if current is None:
            return
        hass.async_create_task(
            _log_action(
                hass,
                current,
                current["config"][CONF_DEFAULT_ACTION],
                person_name,
                scanner_device_id,
            )
        )

    cancel = async_call_later(hass, window, _commit)
    hass.data[DOMAIN]["pending"][tag_id] = {
        "entry_id": entry_id,
        "scanner_device_id": scanner_device_id,
        "person": person_name,
        "cancel": cancel,
    }


def build_menu_actions(
    token: str, actions: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """Build actionable notification buttons for an action menu."""
    return [
        {
            "action": f"{MENU_ACTION_PREFIX}{token}|{action[CONF_ACTION_KEY]}",
            "title": action.get(CONF_ACTION_LABEL, action[CONF_ACTION_KEY]),
        }
        for action in actions
    ]


def parse_menu_action(raw_action: str) -> tuple[str, str] | None:
    """Return (token, action_key) for one of our notification buttons."""
    if not raw_action.startswith(MENU_ACTION_PREFIX):
        return None
    token, separator, action_key = raw_action[len(MENU_ACTION_PREFIX) :].partition("|")
    if not token or not separator or not action_key:
        return None
    return token, action_key


def _notify_service_candidates(hass: HomeAssistant, entity_entry: Any) -> list[str]:
    """Candidate legacy notify service names for a notify entity."""
    candidates = [f"mobile_app_{entity_entry.entity_id.split('.', 1)[1]}"]
    for name in (entity_entry.name, entity_entry.original_name):
        if name:
            candidates.append(f"mobile_app_{_slugify(name)}")
    device = dr.async_get(hass).async_get(entity_entry.device_id)
    if device is not None:
        for name in (device.name, device.name_by_user):
            if name:
                candidates.append(f"mobile_app_{_slugify(name)}")
    return candidates


def _resolve_notify_service(
    hass: HomeAssistant, entry_data: dict, scanner_device_id: str
) -> str | None:
    """Return a legacy notify service that supports actionable buttons."""
    notify_services = hass.services.async_services().get("notify", {})
    configured = entry_data["config"].get(CONF_NOTIFY_SERVICE)
    if configured and configured in notify_services:
        return configured
    if not scanner_device_id:
        return None

    ent_reg = async_get_entity_registry(hass)
    for entity_entry in ent_reg.entities.get_entries_for_device_id(scanner_device_id):
        if entity_entry.domain != "notify":
            continue
        for candidate in _notify_service_candidates(hass, entity_entry):
            if candidate in notify_services:
                return candidate
    return None


def _resolve_person_notify_service(
    hass: HomeAssistant, person_entity_id: str
) -> str | None:
    """Resolve a person's phone to a legacy notify service."""
    state = hass.states.get(person_entity_id)
    if state is None:
        return None
    notify_services = hass.services.async_services().get("notify", {})
    ent_reg = async_get_entity_registry(hass)
    for tracker_id in state.attributes.get("device_trackers") or []:
        tracker_entry = ent_reg.async_get(tracker_id)
        if tracker_entry is None or tracker_entry.device_id is None:
            continue
        for entity_entry in ent_reg.entities.get_entries_for_device_id(
            tracker_entry.device_id
        ):
            if entity_entry.domain != "notify":
                continue
            for candidate in _notify_service_candidates(hass, entity_entry):
                if candidate in notify_services:
                    return candidate
    return None


async def _send_action_menu(
    hass: HomeAssistant,
    entry_data: dict,
    scanner_device_id: str,
    person_name: str,
) -> None:
    """Send the actionable notification for a double scan."""
    config = entry_data["config"]
    service = _resolve_notify_service(hass, entry_data, scanner_device_id)
    if service is None:
        _LOGGER.debug(
            "No notify service for scanner %s; logging default action instead",
            scanner_device_id,
        )
        await _log_action(
            hass,
            entry_data,
            config[CONF_DEFAULT_ACTION],
            person_name,
            scanner_device_id,
        )
        return

    token = uuid4().hex
    hass.data[DOMAIN]["menus"][token] = {
        "entry_id": entry_data["entry_id"],
        "scanner_device_id": scanner_device_id,
        "person": person_name,
    }

    @callback
    def _expire(_now: datetime) -> None:
        hass.data[DOMAIN]["menus"].pop(token, None)

    async_call_later(hass, MENU_TTL_SECONDS, _expire)

    try:
        await hass.services.async_call(
            "notify",
            service,
            {
                "message": "What did you do?",
                "title": config.get(CONF_NAME),
                "data": {
                    "actions": build_menu_actions(token, config[CONF_ACTIONS]),
                    "tag": f"{DOMAIN}_{token}",
                },
            },
            blocking=True,
        )
    except HomeAssistantError as err:
        _LOGGER.warning("Could not send NFC Tasgs action menu: %s", err)
        hass.data[DOMAIN]["menus"].pop(token, None)
        await _log_action(
            hass,
            entry_data,
            config[CONF_DEFAULT_ACTION],
            person_name,
            scanner_device_id,
        )


@callback
def _handle_notification_action(hass: HomeAssistant, event: Any) -> None:
    """Log the action chosen in a double-scan notification."""
    parsed = parse_menu_action(event.data.get("action", ""))
    if parsed is None:
        return
    token, action_key = parsed
    menu = hass.data[DOMAIN].get("menus", {}).pop(token, None)
    if menu is None:
        return
    entry_data = hass.data[DOMAIN]["entries"].get(menu["entry_id"])
    if entry_data is None:
        return
    hass.async_create_task(
        _log_action(
            hass,
            entry_data,
            action_key,
            menu["person"],
            menu["scanner_device_id"],
        )
    )


async def _handle_log(hass: HomeAssistant, call: ServiceCall) -> None:
    entry_data = _get_entry_data(hass, call)
    if not entry_data:
        raise ServiceValidationError("No device targeted")

    await _log_action(
        hass,
        entry_data,
        call.data["action_key"],
        call.data.get("scanner", "Manual"),
        "",
    )


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
            "last_overdue_notify_ts": 0.0,
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
    rec["last_overdue_notify_ts"] = 0.0


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


async def _async_check_overdue(
    hass: HomeAssistant, now: datetime | None = None
) -> None:
    """Notify once per cooldown for every overdue action."""
    now_ts = (now or datetime.now(UTC)).timestamp()
    changed = False
    for entry_data in list(hass.data[DOMAIN].get("entries", {}).values()):
        config = entry_data["config"]
        service = _resolve_notify_service(hass, entry_data, "")
        if not service:
            for person_entity_id in [
                config.get(CONF_ASSIGNEE),
                *(config.get(CONF_OWNERS) or []),
            ]:
                if not person_entity_id:
                    continue
                service = _resolve_person_notify_service(hass, person_entity_id)
                if service:
                    break
        if not service:
            continue
        for action in config[CONF_ACTIONS]:
            action_key = action[CONF_ACTION_KEY]
            rec = entry_data["history"].get(action_key)
            if not rec or rec.get("total_scans", 0) == 0:
                continue
            interval = _compute_interval(
                rec.get("first_scan_ts", 0),
                rec.get("last_scan_ts", 0),
                rec.get("total_scans", 0),
            )
            due = _compute_next_due(
                rec.get("last_scan_ts", 0),
                interval,
                action.get(CONF_ACTION_INTERVAL),
            )
            if due is None or now_ts <= due:
                continue
            last_notified = rec.get("last_overdue_notify_ts", 0.0)
            if now_ts - last_notified < OVERDUE_NOTIFY_COOLDOWN_HOURS * 3600:
                continue
            rec["last_overdue_notify_ts"] = now_ts
            changed = True
            label = action.get(CONF_ACTION_LABEL, action_key)
            due_dt = datetime.fromtimestamp(due, tz=UTC)
            due_str = due_dt.isoformat()
            hass.bus.async_fire(
                EVENT_OVERDUE,
                {
                    ATTR_DEVICE_ID: entry_data["slug"],
                    ATTR_DEVICE_NAME: config.get(CONF_NAME),
                    ATTR_ACTION_KEY: action_key,
                    ATTR_ACTION_LABEL: label,
                    "due": due_str,
                },
            )
            try:
                await hass.services.async_call(
                    "notify",
                    service,
                    {
                        "message": (
                            f"{label} was due {due_dt.strftime('%Y-%m-%d %H:%M')}"
                        ),
                        "title": config.get(CONF_NAME),
                    },
                    blocking=False,
                )
            except HomeAssistantError as err:
                _LOGGER.warning("Could not send overdue notification: %s", err)
    if changed:
        await _save_history(hass)


def _register_services(hass: HomeAssistant) -> None:
    async def scan_service(call: ServiceCall) -> None:
        await _handle_scan(hass, call)

    async def log_service(call: ServiceCall) -> None:
        await _handle_log(hass, call)

    async def reset_service(call: ServiceCall) -> None:
        await _handle_reset(hass, call)

    async def assignee_service(call: ServiceCall) -> None:
        await _handle_set_assignee(hass, call)

    async def check_overdue_service(call: ServiceCall) -> None:
        await _async_check_overdue(hass)

    hass.services.async_register(DOMAIN, SERVICE_SCAN, scan_service)
    hass.services.async_register(DOMAIN, SERVICE_LOG, log_service)
    hass.services.async_register(DOMAIN, SERVICE_RESET_ACTION, reset_service)
    hass.services.async_register(DOMAIN, SERVICE_SET_ASSIGNEE, assignee_service)
    hass.services.async_register(DOMAIN, SERVICE_CHECK_OVERDUE, check_overdue_service)

    if not hass.data[DOMAIN].get("event_listener_registered"):
        hass.bus.async_listen(
            EVENT_NOTIFICATION_ACTION,
            partial(_handle_notification_action, hass),
        )
        hass.bus.async_listen(
            "tag_scanned",
            partial(_handle_tag_scanned, hass),
        )
        hass.data[DOMAIN]["event_listener_registered"] = True
