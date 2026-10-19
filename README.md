# NFC Tasgs

Turn any physical object into a tracked chore with an NFC tag. Scan a tag to
log what you did, who did it, and when. NFC Tasgs learns each action's real
rhythm and tells you when something is due again.

A custom integration for Home Assistant (no YAML required).

---

## Features

- **One config entry per object.** Each object has a tag, a default action, and
  any number of named actions (`cleaned`, `descaled`, `filter_replaced`, …).
- **Single scan logs, double scan asks.** A single tap logs the default action
  after a short window. Tapping twice within that window opens an actionable
  notification with the object's action menu.
- **Self-learning intervals.** The integration measures the real average time
  between scans. A seed interval bootstraps the first reminder; after two scans
  the measured average takes over and keeps improving.
- **Overdue reminders.** An hourly check notifies you when an action is past
  its next due time (at most once per 24 hours per action).
- **Who did it.** The scanner's phone is resolved to the matching person via
  the person's device trackers.
- **Todo hooks.** Actions can add an item to a shopping list or complete a
  matching item in a task list.
- **Everything in the UI.** Devices and actions are edited with the config and
  options flows; the integration listens to `tag_scanned` itself, so no
  blueprint or helper is required.

---

## Installation

### HACS (custom repository)

1. HACS → Integrations → Custom repositories.
2. Add `https://github.com/RenanAz/NFC-Tasgs` as an **Integration**.
3. Install **NFC Tasgs** and restart Home Assistant.

### Manual

Copy `custom_components/nfc_tasgs/` into your Home Assistant `config/custom_components/`
directory and restart.

**Minimum Home Assistant version:** 2026.10.

---

## Getting started

1. **Create the tags first.** In Home Assistant go to **Settings → Tags**, add a
   tag, and write it to an NFC sticker/card with the companion app. Give each
   tag a recognisable name (e.g. “Coffee machine”).
2. **Add the integration.** **Settings → Devices & services → Add integration →
   NFC Tasgs**.
3. Fill in the device step:
   - **Device name** — e.g. `Coffee Machine`.
   - **Tag ID** — pick the tag created in step 1 (the UUID shown in the tag
     dialog).
   - **Actions** — add at least one action. The first action is a good default.
   - **Default action** — chosen on the last step of the flow.
   - **Owners / assignee** — optional people used as notification fallbacks.
   - **Notification service** — optional, e.g. `mobile_app_your_phone`. Needed
     for the double-scan action menu; it is auto-detected from the scanning
     phone when possible.
   - **Task list / shopping list** — optional todo entities for the hooks below.
   - **Double scan window** — seconds between taps to count as a double scan
     (default `3`).
   - **Handle tag scans automatically** — leave on to let the integration
     process its own tags. Turn off if you want to call the service from your
     own automation.
4. Repeat for every object.

Actions can be added, edited, or removed later from the integration's
**Configure** button. Removing an action leaves its old entities behind as
unavailable; delete them from the entity registry if you no longer want them.

---

## How a scan is handled

```
tag_scanned event
      │
      ▼
integration finds the device by tag ID
      │
      ├─ action supplied? ──────────────► log immediately
      │
      ├─ second scan within window? ────► actionable notification menu
      │                                      └─ button tap logs the action
      │
      └─ first scan ─────────────────────► wait for the window
                                             └─ log the default action
```

- If **no notification service** can be resolved, a double scan falls back to
  logging the default action.
- Action buttons carry a short-lived token, so taps from old notifications are
  ignored after five minutes.
- Android shows at most three notification actions; menus with more actions may
  hide the extra buttons. iOS shows more.

---

## Configuration reference

### Device fields

| Field | Description |
|---|---|
| `name` | Display name. Also used in entity names and notifications. |
| `tag_id` | UUID of the NFC tag from Home Assistant's tag registry. |
| `default_action_key` | Action logged by a single scan. |
| `actions` | One or more action definitions. |
| `icon` | Icon used by the device. |
| `area_id` | Optional Home Assistant area. |
| `owners` | Optional `person` entities. |
| `assignee` | Optional `person` entity; can be changed with the service. |
| `double_scan_window_seconds` | Window for detecting a double scan. |
| `auto_scan` | Process `tag_scanned` events automatically (default on). |
| `notify_service` | Legacy notify service used for action menus, e.g. `mobile_app_pixel_9`. |
| `task_list` | Optional `todo` entity for `triggers_task`. |
| `shopping_list` | Optional `todo` entity for `triggers_purchase`. |

### Action fields

| Field | Description |
|---|---|
| `key` | Lowercase identifier (`[a-z0-9_]+`), unique per device. |
| `label` | Text shown in entities, events, and notifications. |
| `expected_interval_hours` | Optional seed interval. Used until the measured average takes over. |
| `triggers_purchase` | Add `"<label> (<device>)"` to the shopping list when logged. Duplicates are skipped. |
| `triggers_task` | Complete an open task with the same summary when logged. |

---

## Self-learning intervals

For each action the integration stores the first scan, the last scan, and the
number of scans.

| Scans | `interval_hours` | `next_due` |
|---|---|---|
| 0 | unknown | unknown |
| 1 | unknown | `last_scan + seed` (if a seed is set) |
| ≥ 2 | `(last - first) / (count - 1)` hours | `last_scan + interval` |

The seed is only a bootstrap. As soon as two scans exist, the measured average
drives both `next_due` and the overdue binary sensor, so the reminders adapt to
your real habits.

`overdue` is `on` when `now > next_due` and the action has been scanned at
least once.

---

## Entities

### Per device

| Entity | Description |
|---|---|
| `sensor.<device>_total_scans` | All actions combined (`total_increasing`). |
| `sensor.<device>_last_scan` | Timestamp of the most recent scan. |
| `sensor.<device>_last_action` | Label of the most recent action. |
| `sensor.<device>_last_scanner` | Person resolved from the scanning phone. |
| `button.<device>_log_manually` | Logs the default action without a tag. |

### Per action

| Entity | Description |
|---|---|
| `sensor.<device>_<action>_last_scan` | Timestamp of the last scan. |
| `sensor.<device>_<action>_interval` | Learned average interval in hours. |
| `sensor.<device>_<action>_next_due` | Estimated next due time. |
| `sensor.<device>_<action>_last_scanner` | Person who last performed the action. |
| `sensor.<device>_<action>_total_scans` | Scan count for this action. |
| `binary_sensor.<device>_<action>_overdue` | On when the action is past due. |

---

## Services

| Service | Fields | Description |
|---|---|---|
| `nfc_tasgs.scan` | `tag_id`, `scanner_device_id`, `action?` | Process a scan. Without `action`, the double-scan window applies. |
| `nfc_tasgs.log` | `device_id`, `action_key`, `scanner` | Log an action manually. |
| `nfc_tasgs.reset_action` | `device_id`, `action_key` | Reset one action's history and counters. |
| `nfc_tasgs.set_assignee` | `device_id`, `person` | Change the assignee (persisted). |
| `nfc_tasgs.check_overdue` | — | Run the overdue check immediately. |

---

## Events

### `nfc_tasgs_action`

Fired after every logged action:

```json
{
  "device_id": "coffee_machine",
  "device_name": "Coffee Machine",
  "action_key": "beans_refilled",
  "action_label": "Beans Refilled",
  "scanner": "Jane",
  "scanner_device_id": "…",
  "timestamp": "2026-10-19T18:00:00+00:00",
  "scan_count": 12,
  "action_scan_count": 4,
  "mode": "scan",
  "interval_hours": 92.5
}
```

`mode` is `scan` for tag scans and `manual` for `nfc_tasgs.log`.

### `nfc_tasgs_overdue`

Fired when an overdue notification is sent:

```json
{
  "device_id": "coffee_machine",
  "device_name": "Coffee Machine",
  "action_key": "descaled",
  "action_label": "Descaled",
  "due": "2026-10-18T09:00:00+00:00"
}
```

---

## Todo hooks

- **Shopping list** (`triggers_purchase`): adds `"<label> (<device>)"` when the
  action is logged. If an open item with that summary already exists, nothing is
  added.
- **Task list** (`triggers_task`): if an open item with that summary exists, it
  is marked completed. No item is created automatically.

Both require the matching `todo` entity to be selected in the device options.

---

## Data

Scan history is stored in `.storage/nfc_tasgs.history` (per config entry and
action). Statistics sensors expose long-term statistics through Home Assistant's
recorder. Removing an action or a device leaves historical statistics in the
recorder; remove the entities manually if you want them gone.

---

## Troubleshooting

- **Double scan logs the default action instead of opening the menu** — no
  notification service could be resolved. Set `notify_service` explicitly
  (e.g. `mobile_app_your_phone`).
- **Scan shows `Unknown` as scanner** — the phone's device tracker is not in any
  person's device trackers. Add it under **Settings → People**.
- **Wrong tag** — check the tag UUID in **Settings → Tags** matches the device.
- **Integration will not load** — check **Settings → System → Logs** for
  `nfc_tasgs`. A stale folder such as `custom_components/nfc_tasgs.bak` must be
  moved out of `custom_components/`.

---

## Development

```bash
ruff check .
ruff format --check .
pytest tests -q
```

The integration lives in `custom_components/nfc_tasgs/`; `tests/` and tooling
are development-only. See `CONTRIBUTING.md` for the branch/PR workflow.
