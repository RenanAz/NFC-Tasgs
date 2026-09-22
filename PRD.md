# PRD — NFC Tasgs (Home Assistant Custom Component)

| Field | Value |
|---|---|
| Domain | `nfc_tasgs` |
| Version | `0.1.0` (`manifest.json`) |
| Author | @renan |
| Repository | https://github.com/RenanAz/NFC-Tasgs |
| Type | Custom integration (`iot_class: local_push`, no `requirements`) |
| Document | PRD compiled from an inventory of the **source code** (not the spec) |
| Production state | **Integration fails to load** — `setup_error` (see §8) |

> This document describes what the **code actually implements**. The project's
> `README.md` is an *aspirational specification*: it describes functionality the
> code does **not** implement yet. The gaps are listed in §9.

---

## 1. Overview

NFC Tasgs turns a physical object (coffee machine, litter box, fries box) into an
NFC-tracked "device". Tapping a phone on the tag fires the companion app's
`tag_scanned` event; an automation blueprint turns that into a service call to the
integration, which logs the action, identifies who did it, and recomputes statistics
(average interval, next due date, overdue state).

The intended differentiator is the **self-learning interval**: the integration learns
each action's real cadence from scan history and exposes an overdue binary sensor.

Each integration *device* = one config entry, with its own set of **actions**
(e.g. `cleaned`, `beans_refilled`). Each action produces sensors plus an overdue
binary sensor.

---

## 2. File inventory

| File | Role | State |
|---|---|---|
| `__init__.py` | Setup, service registration, persistence, person resolution, event emission, interval math | Implemented |
| `config_flow.py` | Config flow (UI) + options flow | Implemented (JSON-based UX) |
| `const.py` | Constants (`DOMAIN`, `CONF_*`, `ATTR_*`, services, platforms, defaults) | Implemented |
| `sensor.py` | Device-level and per-action sensors | Implemented |
| `binary_sensor.py` | Per-action "overdue" binary sensor | **Broken — syntax error** |
| `button.py` | Per-device "Log manually" button | Implemented |
| `services.yaml` | Definitions for the 4 services | Implemented |
| `strings.json` / `translations/en.json` | Config flow labels | Implemented |
| `blueprints/tag_scan.yaml` | Scan → service automation blueprint | Implemented, with issues (§8) |
| `manifest.json` | Integration metadata | Implemented |
| `README.md` | Specification (aspirational) | Diverges from code |
| `const.py: ACTION_SENSORS` / `DEVICE_SENSORS` | Sensor-type lists | `DEVICE_SENSORS` is unused |

---

## 3. Config flow (UI)

### 3.1 Create device — `async_step_user` (`config_flow.py:38`)

Fields (`config_flow.py:62`):

| Field | Key | Required | Default |
|---|---|---|---|
| Device name | `name` (CONF_NAME) | Yes | — |
| Tag ID (UUID) | `tag_id` | Yes | — |
| Default action key | `default_action_key` | Yes | `"default"` |
| Actions (JSON) | `actions_json` | No | `""` |
| Icon | `icon` | No | `mdi:clipboard-check` |
| Owners | `owners` | No | `""` (CSV) |
| Area ID | `area_id` | No | `""` |
| Assignee | `assignee` | No | `""` |
| Double scan window (s) | `double_scan_window_seconds` | No | `3` |

- Actions are entered as a **JSON string** (no structured editor). Expected format:
  `[{"key","label","expected_interval_hours","triggers_purchase","triggers_task"}]`
  (`config_flow.py:82`).
- `_parse_actions_json` (`config_flow.py:189`) parses leniently: invalid JSON or an item
  without `key` is **silently dropped** (returns `[]`).
- `owners` is parsed by `_parse_list` as a comma-separated list (`config_flow.py:215`).

### 3.2 Edit device — options flow `async_step_init` (`config_flow.py:95`)

- Additional fields: `task_list`, `shopping_list` (todo entities), plus every create
  field except `name`/`tag_id`.
- If `actions_json` is submitted empty, the current actions are kept
  (`config_flow.py:100`).
- This is the only path where `task_list` / `shopping_list` can be set (they do not exist
  in the create step).

---

## 4. Entities created

All attributes set `_attr_has_entity_name = True` and `device_info` pointing at the
virtual device created in `__init__.py:107` (`identifiers={(DOMAIN, entry_id)}`,
manufacturer `NFC Tasgs`, model `Virtual Chore Device`).

### 4.1 Per device (`sensor.py:42`)

| Entity | Type | Details |
|---|---|---|
| `sensor.<device>_total_scans` | sensor | Sum of scans across all actions; `total_increasing`; unit `scans` |
| `sensor.<device>_last_scan` | sensor | `device_class: timestamp`; `None` if never scanned |
| `sensor.<device>_last_action` | sensor | Label of the most recent action |
| `sensor.<device>_last_scanner` | sensor | Name of the last person to scan |

### 4.2 Per action (`sensor.py:55`) — 5 sensors

Created for **every** action, even without `expected_interval_hours`.

| Entity | Type / class | Computation |
|---|---|---|
| `..._last_scan` | `timestamp` | Action's `last_scan_ts` |
| `..._interval_hours` | `measurement`, unit `h` | Moving average (see §7); `None` if `total_scans < 2` |
| `..._next_due` | `timestamp` | `last_scan + interval`, or seed (see §7) |
| `..._last_scanner` | text | Last scanner for the action |
| `..._total_scans` | `total_increasing`, unit `scans` | Action counter |

### 4.3 Per action (`binary_sensor.py:37`) — 1 binary sensor

| Entity | Description |
|---|---|
| `binary_sensor.<device>_<action>_overdue` | `on` when `now > next_due`; `None` if `total_scans == 0` |

### 4.4 Per device (`button.py:25`)

| Entity | Description |
|---|---|
| `button.<device>_log_manual` | Calls `nfc_tasgs.log` with the default action and `scanner="Manual"` |

### 4.5 Naming

`unique_id` = `{slug}_{sensor_type}` or `{slug}_{action_key}_{sensor_type}`, where
`slug = _slugify(name)` (`__init__.py:66`) — lowercase, spaces/hyphens → `_`, apostrophe
removed. **Risk:** two devices with the same name collide (identical `slug`).

---

## 5. Services (`services.yaml`, registered in `__init__.py:391`)

### 5.1 `nfc_tasgs.scan`

| Field | Required | Description |
|---|---|---|
| `tag_id` | Yes | UUID of the scanned tag |
| `scanner_device_id` | Yes | HA device ID of the scanning phone |
| `action` | No | Action key; if omitted, uses the device's default action |

Flow (`__init__.py:238`): find the entry by `tag_id` → resolve person → write the scan
into history → save → refresh entities → fire event. Raises `ServiceValidationError` if
the tag belongs to no device or the action does not exist.

### 5.2 `nfc_tasgs.log`

Target: device (filter `integration: nfc_tasgs`). Fields: `action_key` (required),
`scanner` (required). Logs without a tag (`scanner_device_id` empty).

### 5.3 `nfc_tasgs.reset_action`

Target: device. Field `action_key`. Zeroes the counters and history for that action
(`__init__.py:303`).

### 5.4 `nfc_tasgs.set_assignee`

Target: device. Field `person` (string; empty clears). **Only mutates
`entry_data["config"][CONF_ASSIGNEE]` in memory** (`__init__.py:321`). It does not
persist to storage or the config entry, does not refresh entities, and fires no event —
the value is lost on the next reload.

---

## 6. Audit event

Every operation (`scan` or `log`) fires the **`nfc_tasgs_action`** event
(`__init__.py:349`, `const.py:34`) with:

```json
{
  "device_id": "<slug>",
  "device_name": "<name>",
  "action_key": "<key>",
  "action_label": "<label>",
  "scanner": "<name or Unknown>",
  "scanner_device_id": "<device id or ''>",
  "timestamp": "<ISO UTC>",
  "scan_count": <sum over all actions>,
  "action_scan_count": <count for the action>,
  "mode": "<'scan' if a device_id was present, else 'manual'>",
  "interval_hours": <round 1 or null>
}
```

Note: the README documents `mode: "double_scan"`, but the code only emits `"scan"` or
`"manual"`.

---

## 7. Self-learning interval system

Functions in `__init__.py`:

- `_compute_interval(first, last, count)` (`:70`): `count < 2` → `None`; otherwise
  `(last - first) / 3600 / (count - 1)` (moving average in hours).
- `_compute_next_due(last, interval, seed)` (`:76`): if `interval` exists → `last +
  interval*3600`; else if `seed` exists → `last + seed*3600` (or `now + seed*3600` when
  `last == 0`); else `None`.

Effective rule:

| Condition | `interval_hours` | `next_due` | `overdue` |
|---|---|---|---|
| `total_scans < 2` | `None` | seed if present, else `None` | `None` (never) |
| `total_scans >= 2` | moving average | `last + interval` | `now > next_due` |

Divergence from the README: the README promises `overdue` driven by the seed even with
**zero** scans ("seed set, no data"); the code returns `None` while `total_scans == 0`
(`binary_sensor.py:93`).

---

## 8. Current state and known defects

### 8.1 BLOCKER — syntax error in `binary_sensor.py`

The `NfcTasgsOverdueSensor` class was corrupted by a bad merge/paste: the `is_on`
definition and the dispatcher block got tangled with string literals
(`binary_sensor.py:73-87`):

```python
    @property
    def is_on(self) -> bool | None:","@callback
    def _handle_update(self) -> None:
        ...
    @property
    def is_on(self) -> bool | None:"}
```

HA system-log evidence:

```
File "/config/custom_components/nfc_tasgs/binary_sensor.py", line 87
    def is_on(self) -> bool | None:"}
SyntaxError: unterminated string literal (detected at line 87)
```

Because `__init__.py:135` imports `binary_sensor` before forwarding platforms, **the whole
integration fails** and the "Caixa da Fritas" config entry
(`01KXG65NFM8SA24GZTSS06TCQR`) is stuck in `setup_error`.

### 8.2 Blueprint points at nonexistent helpers

`blueprints/tag_scan.yaml` references `input_text.nfc_tasgs_pending`
(`:45,59,71,85,97,106,118`) and `timer.nfc_tasgs_scan_window` (`:26,51,57,76`). Those do
not exist on the live HA — the actual ones are `input_text.chore_tracker_pending` and
`timer.chore_tracker_window`. The integration does **not** provision these helpers, so
the blueprint cannot work as written.

### 8.3 Blueprint: notification action field

`tag_scan.yaml:108` reads `trigger.event.data.actionKey`. The companion app's
`mobile_app_notification_action` event exposes `action`, not `actionKey` — the
double-scan menu never resolves the chosen action.

### 8.4 Configured but unused fields

`owners`, `assignee`, `task_list`, `shopping_list`, `icon`,
`double_scan_window_seconds`, `triggers_purchase`, `triggers_task` are collected in the
config flow and persisted, but **no logic consumes them** in the current code.

### 8.5 Double-scan semantics live outside the integration

The README states the `scan` service detects double scans. The code does not: all
detection lives in the blueprint via external helpers. The
`double_scan_window_seconds` configured on the entry is never read by the integration.

### 8.6 Other risks / code smells

- `set_assignee` does not persist (§5.4).
- `_refresh_entities` (`:386`) emits a **global** signal (`SIGNAL_UPDATE`) to all
  entries; it works, but is not scoped per entry.
- `timestamp` sensors return an **ISO string** (`sensor.py:133,214,243`) instead of a
  `datetime`; this relies on HA's parsing tolerance.
- `_parse_actions_json` fails silently: a single typo in the JSON wipes all actions.
- Unused imports in `__init__.py` (`asyncio`, `callback`, `_binary_sensor`, etc.).
- `const.py: DEVICE_SENSORS` is unused.
- `hass.data[DOMAIN]["store"]` is created only once and shared across entries;
  `_save_history` writes the history of **all** entries on every call.

---

## 9. Gaps versus the README (not implemented)

| Documented feature | Code state |
|---|---|
| Overdue notifications (owners/assignee) | Not implemented |
| Assignee rotation / fair-share | Not implemented |
| Task-list integration (`triggers_task`) | Not implemented |
| Shopping-list integration / dedup (`triggers_purchase`) | Not implemented |
| Double-scan detection in the integration | Blueprint only (and defective) |
| Auto-generated dashboard | Not implemented |
| `coordinator.py` / `device.py` / `services.py` (from the plan) | Do not exist; logic all in `__init__.py` |
| Robust person resolution | Partially implemented (§10) |
| HACS publication / custom card | Not started |

---

## 10. Person resolution (`__init__.py:217`)

1. Receives `scanner_device_id` (HA device of the phone).
2. Looks up the device in the device registry; if absent → `("Unknown", id)`.
3. Iterates `entity_registry.entities.get_entries_for_device_id(...)` looking for
   `device_tracker.*`.
4. For each `person.*`, checks `person_entry.options["device_trackers"]` and matches the
   `device_tracker`.
5. Returns `person_entry.original_name or person_entry.entity_id`.
6. Fallback: `"Unknown"`.

Limitations: depends on the person's `options.device_trackers`; does not handle a null
`original_name`; no match → `Unknown`.

---

## 11. Data model

### Config entry (`entry.data` + `entry.options`, see `_build_config` `:160`)

```json
{
  "name": "Caixa da Fritas",
  "tag_id": "<uuid>",
  "default_action_key": "cleaned",
  "actions": [
    {"key": "cleaned", "label": "Cleaned",
     "expected_interval_hours": 168,
     "triggers_purchase": false, "triggers_task": false}
  ],
  "icon": "mdi:clipboard-check",
  "owners": ["person.renan"],
  "assignee": null,
  "double_scan_window_seconds": 3,
  "task_list": null,
  "shopping_list": null,
  "area_id": null
}
```

Defaults applied in `_build_config`: if there are no `actions`, one action
`{default_key, default_key.title()}` is created.

### History (memory + storage)

`hass.data["nfc_tasgs"]["entries"][entry_id]["history"]`, persisted to
`.storage/nfc_tasgs.history` (`STORAGE_VERSION=1`, `_save_history` `:209`):

```json
{
  "<action_key>": {
    "first_scan_ts": 0.0,
    "last_scan_ts": 0.0,
    "total_scans": 0,
    "last_scanner": "",
    "last_scanner_device_id": ""
  }
}
```

Storage key: history per `entry_id`. Config is NOT in storage (it comes from the entry).

---

## 12. Observed non-functional requirements

- **Persistence:** history in `.storage` via `Store`; saved on every scan/reset.
  `assignee` is not persisted.
- **Reactivity:** entities refreshed via `dispatcher` (`SIGNAL_UPDATE`), no polling.
- **Config:** 100% UI (config entry), no YAML — aligned with the README.
- **No external dependencies** (`requirements: []`).
- **Setup idempotence:** services are registered once via the `services_registered` flag.
- **Reload:** option changes trigger `_update_listener` → `async_reload`.

---

## 13. Recommended next steps (suggested order)

1. **Fix `binary_sensor.py`** — rewrite `NfcTasgsOverdueSensor` (inherit the dispatcher
   from a shared base) to clear the `setup_error`.
2. Align the blueprint with the real helpers (`chore_tracker_*`) **or** make the
   integration provision the helpers.
3. Fix the notification event field (`action` instead of `actionKey`).
4. Persist `assignee` (storage/entry) and refresh entities on change.
5. Decide scope: actually implement `owners`/`triggers_purchase`/`triggers_task` and
   notifications (README Phases 2/3) — or remove them from the PRD/README.
6. Harden `actions_json` parsing (report an error instead of discarding).
7. Cover double-scan inside the integration (or document the helper dependency).
8. Scope `SIGNAL_UPDATE` per entry and remove dead code/imports.
