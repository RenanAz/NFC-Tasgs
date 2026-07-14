# NFC Tasgs — Specification

A Home Assistant custom integration that turns any physical object into a trackable "chore device" via NFC tags. Scan a tag to log maintenance actions, identify who performed them, derive per-action statistics (average interval, next due date, who does it most), and receive adaptive reminders when something is due.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    CONFIG FLOW (UI)                       │
│  Define devices: name, tag_id, actions[], owners[],       │
│  assignee, default_action                                 │
│                                                           │
│  Per action: key, label, expected_interval_hours (seed),  │
│  triggers_purchase, triggers_task                         │
└──────────────────────┬───────────────────────────────────┘
                       │ creates
                       ▼
┌──────────────────────────────────────────────────────────┐
│                  PER-DEVICE ENTITIES                       │
│  sensor.<device>_total_scans    (total_increasing, LTS)   │
│  sensor.<device>_last_scan      (timestamp)               │
│  sensor.<device>_last_action    (action label)            │
│  sensor.<device>_last_scanner   (person name)             │
│  button.<device>_log_manual     (logs default action)     │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│               PER-ACTION ENTITIES (all actions)            │
│  sensor.<device>_<action>_last_scan        (timestamp)    │
│  sensor.<device>_<action>_interval         (hours, LTS)   │
│  sensor.<device>_<action>_next_due         (datetime)     │
│  sensor.<device>_<action>_last_scanner     (text)         │
│  sensor.<device>_<action>_total_scans      (total_inc)    │
│  binary_sensor.<device>_<action>_overdue   (on/off)       │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│                    INTEGRATION SERVICES                   │
│  nfc_tasgs.scan(tag_id, device_id, action?)                │
│  nfc_tasgs.log(device_id, action_key, scanner)             │
│  nfc_tasgs.reset_action(device_id, action_key)             │
│  nfc_tasgs.set_assignee(device_id, person)                 │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│                    AUTOMATION (Blueprint)                 │
│  Triggers: tag_scanned event                             │
│  Resolves: tag_id → device, device_id → person           │
│  Single scan: calls nfc_tasgs.scan (default action)       │
│  Double scan: sends actionable notification with menu     │
│  Notification tap: calls nfc_tasgs.scan with chosen action │
└──────────────────────────────────────────────────────────┘
```

---

## Configuration

### Per-device fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Display name (e.g. "Coffee Machine") |
| `tag_id` | string | Yes | NFC tag UUID from HA's tag registry |
| `default_action` | string | Yes | Action key logged on single scan |
| `actions` | list[object] | Yes | List of action definitions (see below) |
| `owners` | list[person_id] | No | People responsible for this device |
| `assignee` | person_id | No | Currently assigned person |
| `double_scan_window_seconds` | int | `3` | Time window to detect double-scan |
| `task_list` | todo_entity_id | No | Todo list for scheduled tasks/reminders |
| `shopping_list` | todo_entity_id | No | List for purchase-triggering actions |
| `icon` | string | `mdi:clipboard-check` | MDI icon for dashboard |
| `area_id` | string | No | HA area for the physical object |

### Per-action fields

| Field | Type | Required | Description |
|---|---|---|---|
| `key` | string | Yes | Internal key (slug, e.g. `beans_refilled`) |
| `label` | string | Yes | Display label (e.g. "Beans Refilled") |
| `expected_interval_hours` | float | No | Seed interval for reminders. If unset and ≤2 scans exist, the system self-learns from actual data. If unset and ≤1 scan, no interval computed, no overdue alerts. Once ≥3 scans of this action exist, the actual average overrides any seed. |
| `triggers_purchase` | bool | `false` | Logging this action adds an item to `shopping_list` |
| `triggers_task` | bool | `false` | Logging this action creates/completes a task in `task_list` |

### Full config example

```yaml
devices:
  - name: "Coffee Machine"
    tag_id: "a0c60634-0a93-4bfb-bab2-a803e83444da"
    default_action: "cleaned"
    owners:
      - person.renan
      - person.michelle
    task_list: todo.coisas_da_casa
    shopping_list: todo.coisas_da_casa
    actions:
      - key: "cleaned"
        label: "Cleaned"
        expected_interval_hours: 168
      - key: "descaled"
        label: "Descaled"
        expected_interval_hours: 1440
      - key: "beans_refilled"
        label: "Beans Refilled"
        expected_interval_hours: 120
        triggers_purchase: true
      - key: "filter_changed"
        label: "Filter Changed"
        expected_interval_hours: 2160
        triggers_purchase: true

  - name: "Abby's Litter Box"
    tag_id: "140f5515-ea29-4004-8d11-712097f1e9fd"
    default_action: "cleaned"
    owners:
      - person.renan
      - person.michelle
    actions:
      - key: "cleaned"
        label: "Cleaned"
        expected_interval_hours: 48
      - key: "deep_cleaned"
        label: "Deep Cleaned"
      - key: "litter_replaced"
        label: "Litter Replaced"
        triggers_purchase: true

  - name: "Living Room Plants"
    tag_id: "..."
    default_action: "watered"
    actions:
      - key: "watered"
        label: "Watered"
        expected_interval_hours: 96
      - key: "fertilized"
        label: "Fertilized"
        expected_interval_hours: 720
        triggers_purchase: true
      - key: "repotted"
        label: "Repotted"
      - key: "pruned"
        label: "Pruned"
```

---

## Self-learning interval system

The core differentiator. Every action learns its actual rhythm from scan history.

### Algorithm

```
SCAN_COUNT < 2:
  interval = unknown
  next_due = unknown
  overdue = off

SCAN_COUNT == 2:
  interval = (last_scan - first_scan)  # raw interval from 2 data points
  next_due = last_scan + interval
  overdue = expected_interval check if seed exists, else off
  
SCAN_COUNT >= 3:
  interval = (last_scan_timestamp - first_scan_timestamp) / (scan_count - 1)  # running average
  next_due = last_scan + interval
  overdue = now > next_due
```

### Behavior

- **No seed, no data**: sensors report `unknown`, no reminders fire
- **Seed set, no data**: `overdue` fires based on `expected_interval_hours` (assume first scan happened at startup/creation time)
- **Seed set, 1 scan**: same as above — seed acts as the expected interval until data proves otherwise
- **≥2 scans**: seed is ignored. Actual computed interval drives everything. The system adapts.
- **Rare actions** (descaled every 6 months): intervals become increasingly accurate over years of use

### Why this matters

A coffee machine might be configured with `expected_interval_hours: 168` for cleaning (once a week). But in reality, you clean it every 9.5 days because it doesn't get that dirty. The seed bootstraps the first reminder, then the system learns your actual pattern and stops nagging you at day 7.

---

## Entities created

### Per-device entities (5)

| Entity | Domain | Description | LTS |
|---|---|---|---|
| `sensor.<device>_total_scans` | sensor | All actions combined, `state_class: total_increasing` | Yes |
| `sensor.<device>_last_scan` | sensor | ISO timestamp of most recent scan (`device_class: timestamp`) | No |
| `sensor.<device>_last_action` | sensor | Label of last action logged | No |
| `sensor.<device>_last_scanner` | sensor | Name of person who last scanned | No |
| `button.<device>_log_manual` | button | Log default action without a tag scan | — |

### Per-action entities (6 per action)

Created for EVERY action, regardless of whether `expected_interval_hours` is set. Sparse actions (rarely scanned) simply report `unknown` until enough data exists.

| Entity | Domain | Description | LTS |
|---|---|---|---|
| `sensor.<device>_<action>_last_scan` | sensor | ISO timestamp of last time this action was logged (`device_class: timestamp`) | No |
| `sensor.<device>_<action>_interval_hours` | sensor | Running average hours between scans, self-learning (`state_class: measurement`) | Yes |
| `sensor.<device>_<action>_next_due` | sensor | Estimated next due datetime (`device_class: timestamp`) | No |
| `sensor.<device>_<action>_last_scanner` | sensor | Name of person who last performed this action | No |
| `sensor.<device>_<action>_total_scans` | sensor | Count of this specific action, `state_class: total_increasing` | Yes |
| `binary_sensor.<device>_<action>_overdue` | binary_sensor | `on` when `now > next_due` | No |

### Entity naming

Entity IDs follow HA convention: lowercase, ASCII, underscores.

```
sensor.coffee_machine_cleaned_interval_hours
sensor.coffee_machine_descaled_last_scan
binary_sensor.abbys_litter_box_cleaned_overdue
sensor.living_room_plants_fertilized_total_scans
```

### Example: Coffee Machine with 4 actions

```
Device entities (5):
  sensor.coffee_machine_total_scans
  sensor.coffee_machine_last_scan
  sensor.coffee_machine_last_action
  sensor.coffee_machine_last_scanner
  button.coffee_machine_log_manual

Action: cleaned (6):
  sensor.coffee_machine_cleaned_last_scan
  sensor.coffee_machine_cleaned_interval_hours
  sensor.coffee_machine_cleaned_next_due
  sensor.coffee_machine_cleaned_last_scanner
  sensor.coffee_machine_cleaned_total_scans
  binary_sensor.coffee_machine_cleaned_overdue

Action: descaled (6)
Action: beans_refilled (6)
Action: filter_changed (6)

Total: 5 + 24 = 29 entities
```

This is many entities. The dashboard view groups them per device with collapsible cards so the user is not overwhelmed.

---

## Services

### `nfc_tasgs.scan`

Called by the automation when a tag is scanned. Handles person resolution, double-scan detection within the window, counter increment for the correct action, and notification for the double-scan menu.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `tag_id` | string | Yes | UUID of scanned tag |
| `device_id` | string | Yes | HA device ID of the scanning phone |
| `action` | string | No | Action key. If omitted, uses device's `default_action`. Set when notification action is tapped. |

**Single-scan flow**: tag scanned → `nfc_tasgs.scan(tag_id, device_id)` → integration resolves device + person → logs default_action with timestamp → increments counters → updates intervals → fires `nfc_tasgs_action` event.

**Double-scan detection**: the automation (blueprint) handles this. First scan stores pending state and starts a short timer. Second scan of same tag within the window cancels the timer and sends a notification with action buttons. Timer expiry without a second scan auto-calls `nfc_tasgs.scan`.

### `nfc_tasgs.log`

Directly log an action without a tag scan. For dashboard buttons or manual overrides.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `device_id` | string | Yes | Device key from config |
| `action_key` | string | Yes | Action key to log |
| `scanner` | string | Yes | Person name or "Manual" |

### `nfc_tasgs.reset_action`

Reset a specific action's counters and history to 0. Useful when replacing a device or correcting data.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `device_id` | string | Yes | Device key |
| `action_key` | string | Yes | Action to reset |

### `nfc_tasgs.set_assignee`

Change the currently assigned person for a device.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `device_id` | string | Yes | Device key |
| `person` | person_id | Yes | Person entity ID, or empty string to clear |

---

## Person resolution

The `tag_scanned` event carries a `device_id` (the phone that scanned the tag). The integration resolves this to a person:

1. Look up the device in HA's device registry
2. Find associated `device_tracker.*` entities
3. Match `device_tracker` to a `person.*` entity via the person's `device_trackers` attribute
4. Fallback: if no person found, scanner = `"Unknown"`

This works automatically if each person linked their HA Companion app to their user profile during setup. No additional configuration needed.

---

## Notification system

### Overdue alerts

When `binary_sensor.<device>_<action>_overdue` turns `on`, an automation (provided as a blueprint) can:

1. **Notify owners**: ping all owners via their mobile app notify entities
2. **Notify assignee**: if a specific person is assigned, ping only them
3. **Create a task**: add an item to `task_list` if configured

Notification template:

> **[Device Name]** — **[Action Label]** is overdue
> Last done **{interval} days ago** by **{person}**
> Average interval: **{avg_interval} days**
> Next due was: **{next_due_date}**

### Rotating assignee reminders

When multiple owners exist and the same person did the last N actions, the system can ping the owner who has done it **least recently** instead:

```
for each action:
  sort owners by last_scanned_date (null first)
  if current_assignee == last_scanner and others haven't scanned recently:
    nudge the oldest-stale owner
```

This prevents one person from always getting the notification.

---

## Task list integration

### Creating tasks

When `triggers_task: true` is set on an action and the device has a `task_list`:

- **On overdue**: create a task "**[Action Label]** [Device Name]" in the configured todo list
- **On completion**: mark the task as completed automatically when the action is logged
- **Recurring**: immediately create the next instance with a due date based on the learned interval

### Shopping list integration

When `triggers_purchase: true` is set on an action and the device has a `shopping_list`:

- **On action logged**: add item "**[Device Name]** supplies — **[Action Label]**" to the shopping list
- Example: logging "Beans Refilled" on "Coffee Machine" adds "Coffee Machine supplies — Beans Refilled" to `todo.coisas_da_casa`
- **Deduplication**: if the same purchase item is already on the list (incomplete), don't duplicate it

---

## Audit trail

Every scan or manual log fires a custom event `nfc_tasgs_action`:

```json
{
  "event_type": "nfc_tasgs_action",
  "data": {
    "device_id": "coffee_machine",
    "device_name": "Coffee Machine",
    "action_key": "beans_refilled",
    "action_label": "Beans Refilled",
    "scanner": "Renan",
    "scanner_device_id": "eaa1ef3fdbfea647642d5eb5b76b3abe",
    "timestamp": "2026-07-13T22:30:00+01:00",
    "scan_count": 47,
    "action_scan_count": 12,
    "mode": "double_scan",
    "interval_hours": 114.3
  }
}
```

This event appears in the HA logbook, is consumable by any automation, and can be persisted to a local calendar via an optional automation blueprint.

---

## Dashboard

The integration optionally creates an auto-generated dashboard view with one collapsible section per device, showing:

- Total scans (tile card)
- Last action + last scanner (entities card)
- Per-action cards: last scan, interval, next due, overdue status

Users can also manually build custom dashboards using the generated entities.

---

## Automation blueprint

The integration ships with a blueprint (`nfc_tasgs_tag_scan.yaml`) that users import once. It handles:

1. Trigger: `tag_scanned` event
2. Resolve: calls `nfc_tasgs.scan` service
3. Double-scan detection: times window, sends notification with action menu
4. Notification action handling: passes chosen action key back to `nfc_tasgs.scan`

Users don't write any automation YAML — they import the blueprint, done.

---

## 10 Example devices

| # | Device | Actions | Notes |
|---|---|---|---|
| 1 | Cat litter box | cleaned, deep_cleaned, litter_replaced | 48h interval. Litter replaced triggers purchase. |
| 2 | Automatic cat feeder | refilled, deep_cleaned, battery_changed | 72h. Battery changed is rare. |
| 3 | Coffee machine | cleaned, descaled, beans_refilled, filter_changed | Multiple intervals. Beans + filter trigger purchase. |
| 4 | Living room plants | watered, fertilized, repotted, pruned | Watered = frequent (96h). Fertilized = seasonal. |
| 5 | Robot vacuum | maintained, filter_replaced, brush_replaced, bag_emptied | Bag replaced triggers purchase. |
| 6 | Air purifier | filter_checked, filter_replaced, prefilter_washed | Long intervals. Filter replaced triggers purchase. |
| 7 | Fridge water filter | replaced | 6-month interval. Always triggers purchase. |
| 8 | Car maintenance | oil_changed, tires_rotated, filter_replaced, washed | Mix of DIY and professional intervals. |
| 9 | Bicycle | chain_lubed, cleaned, chain_replaced, brake_pads_replaced | Chain replaced + brake pads trigger purchase. |
| 10 | HVAC system | filter_checked, filter_replaced | Seasonal. Filter triggers purchase. |
| 11 | Fish tank | water_changed, filter_cleaned, water_tested, fish_fed | Water changed = frequent. Water tested = purchase trigger. |
| 12 | Grill / BBQ | cleaned, propane_refilled, grates_replaced | Seasonal. Propane triggers purchase. |

---

## Implementation plan

### Phase 1 — Core integration

```
custom_components/nfc_tasgs/
├── __init__.py           # async_setup, async_setup_entry, services
├── config_flow.py         # UI config flow (add/edit/delete devices)
├── const.py               # DOMAIN, ATTR_*, CONF_* constants
├── coordinator.py         # DataUpdateCoordinator for state management
├── device.py              # Per-device state, scan handling, interval calculation
├── sensor.py              # All sensor entities (device-level + per-action)
├── binary_sensor.py       # Overdue binary sensors (per-action)
├── button.py              # Manual log button (per-device)
├── services.py            # Service definitions (scan, log, reset, set_assignee)
├── manifest.json          # Integration metadata
├── strings.json           # English strings
├── translations/          # i18n files
│   └── en.json
├── services.yaml          # Service definitions for HA
├── blueprints/
│   └── tag_scan.yaml      # Automation blueprint
└── README.md              # This document
```

### Phase 2 — Notifications & Task integration

- Overdue notification automation (blueprint)
- Task list integration (`todo.create_item`, `todo.update_item`)
- Shopping list integration (deduplication logic)
- Person rotation / fair-share logic

### Phase 3 — Dashboard & sharing

- Auto-generated dashboard view
- HACS submission
- Custom Lovelace card (optional — cards showing per-action intervals as sparklines)
- Statistics card showing historical interval trends per action

---

## Data model

### Configuration storage

Stored in HA's config entry system (`.storage/core.config_entries`), one entry per device. No YAML file needed.

```json
{
  "devices": [
    {
      "id": "coffee_machine_01",
      "name": "Coffee Machine",
      "tag_id": "a0c60634-0a93-4bfb-bab2-a803e83444da",
      "default_action": "cleaned",
      "owners": ["person.renan", "person.michelle"],
      "assignee": null,
      "double_scan_window_seconds": 3,
      "task_list": "todo.coisas_da_casa",
      "shopping_list": "todo.coisas_da_casa",
      "icon": "mdi:coffee",
      "area_id": null,
      "actions": [
        {
          "key": "cleaned",
          "label": "Cleaned",
          "expected_interval_hours": 168,
          "triggers_purchase": false,
          "triggers_task": false
        }
      ]
    }
  ]
}
```

### Runtime state (per-action scan history)

Stored in memory during runtime, persisted to HA's `restore_state` for survival across restarts. The coordinator tracks, per action:

```python
{
    "first_scan": datetime,        # timestamp of first scan ever
    "last_scan": datetime,          # timestamp of most recent scan
    "total_scans": int,             # cumulative count
    "last_scanner": str,            # person name
    "last_scanner_device_id": str,  # HA device ID
}
```

The `interval_hours` and `next_due` are computed properties, not stored. They derive from the above data at read time.

---

## Key design decisions

1. **Per-action entities, always.** Every action gets its full set of entities regardless of whether an interval is seeded. Actions with no data report `unknown`. This avoids "why isn't there a sensor for this action?" confusion and supports self-learning for all actions.

2. **Seed helps boot, data overrides.** The first interval reminder uses the configured seed. After 2 scans, the actual data takes over. This means the system is useful from day 1 but also adapts to reality.

3. **No YAML configuration.** All device/action config goes through the UI config flow. This makes it accessible to non-technical users and eliminates YAML indentation errors.

4. **Blueprint, not hardcoded automation.** The scan→service bridge lives in a reusable blueprint. Users import once, not per device.

5. **Event-driven audit trail.** Every scan emits a custom event. This is the canonical record. Calendar entries, logbook entries, and external consumers all derive from this event stream.

6. **integration-scoped entity IDs.** Entity IDs use only the device name and action key (`sensor.coffee_machine_cleaned_interval_hours`), not a prefix like `nfc_tasgs.*`. This keeps dashboards clean.
