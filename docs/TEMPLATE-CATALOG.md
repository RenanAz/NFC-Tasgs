# NFC Tasgs — Appliance Template Catalog

**Date:** 2026-10-19
**Status:** implemented on the test build; live rollout pending
**Goal:** replace free-form action creation with a curated appliance preset. The user picks a template, keeps/removes pre-ticked actions, and the integration generates stable keys, entities, and a notification menu.

The catalog lives in `custom_components/nfc_tasgs/templates.py` as data-only Python constants. A JSON split is a possible follow-up once the catalog stabilizes.

---

## 1. Decisions locked in v2

| # | Decision |
|---|---|
| 1 | Double scan skips the default action. The notification has **two quick actions + a permanent third button, “Open Appliance tasks.”** |
| 2 | A scan must **not** add shopping items or tasks automatically. Shopping/list behavior is explicit and user-requested; this is deferred. |
| 3 | Everything user-facing is **English**, including device/action labels. Action vocabulary is consistent. **Cleaned is the default** where the template has a cleaning action; the user can change the default. |
| 4 | “Seed interval” is developer language. The UI says **“How often?”** with day/week/month units and explains that the first reminder adapts after two logs. |
| 5 | Shopping/task item text matures later. No template-level shopping/task hooks in v1. |
| 6 | A “use case” layer is a future addition: it differentiates how the same appliance is used. It is in the pipeline, not v1. |

---

## 2. User flow

1. Pick the tag.
2. **Pick the appliance** — Coffee Machine, Litter Box, Pet Feeder, Water Fountain, AC Unit, Guinea Pig Habitat, Robot Vacuum, Custom.
3. **Pick actions** — checklist with pre-ticked recommended actions. Each row shows the label and “How often?”.
4. **Confirm** — choose the default action from the selected actions. Preview the generated entities.
5. Save.

### “How often?” control

Do not expose hours or the word “seed.”

- Field label: **“How often?”**
- Presets: Every day · Every 2 days · Every 3 days · Every week · Every 2 weeks · Every month · Every 2 months · Every 3 months · Every 6 months · Custom
- Helper text: **“Used for the first reminder. After two logs, NFC Tasgs follows your actual rhythm.”**
- Preview line: **“First reminder: in 1 week.”**

Internally the value remains `interval_hours`; only the presentation changes.

### Preview

```
Template: Coffee Machine
Selected 4 of 6 actions · Default: Cleaned

sensor.cafe_cleaned_last_scan
sensor.cafe_cleaned_interval
sensor.cafe_cleaned_next_due
sensor.cafe_cleaned_last_scanner
sensor.cafe_cleaned_total_scans
binary_sensor.cafe_cleaned_overdue
...
Double-scan menu: Beans Refilled · Descaled · Open Appliance tasks
```

The preview must come from the same slug/unique-ID helpers used by the entity platforms.

---

## 3. Action vocabulary

Keep verbs and nouns consistent across templates.

| Canonical label | Key | Use |
|---|---|---|
| Cleaned | `cleaned` | Routine cleaning; default where present |
| Deep Cleaned | `deep_cleaned` | Less frequent thorough clean |
| Filter Replaced | `filter_replaced` | Physical filter cartridge |
| Descaled | `descaled` | Coffee machine descaling |
| Beans Refilled | `beans_refilled` | Coffee beans |
| Milk System Cleaned | `milk_system_cleaned` | Espresso milk path |
| Litter Replaced | `litter_replaced` | Litter box substrate |
| Carbon Filter Replaced | `carbon_filter_replaced` | Litter box filter |
| Liner Replaced | `liner_replaced` | Litter box liner |
| Drawer Emptied | `drawer_emptied` | Automatic litter box |
| Food Refilled | `food_refilled` | Pet feeder |
| Desiccant Replaced | `desiccant_replaced` | Automatic feeder |
| Battery Replaced | `battery_replaced` | Battery-powered appliance |
| Water Refilled | `water_refilled` | Fountain / tank |
| Pump Cleaned | `pump_cleaned` | Water fountain |
| Drain Line Flushed | `drain_line_flushed` | AC unit |
| Coils Cleaned | `coils_cleaned` | AC unit |
| Serviced | `serviced` | Professional service |
| Bedding Replaced | `bedding_replaced` | Small pet habitat |
| Hay Refilled | `hay_refilled` | Small pet habitat |
| Water Changed | `water_changed` | Small pet habitat |
| Nail Trimmed | `nail_trimmed` | Pet care |
| Maintained | `maintained` | Robot vacuum exception |
| Bag Emptied | `bag_emptied` | Robot vacuum |
| Brush Replaced | `brush_replaced` | Robot vacuum |
| Mop Pad Cleaned | `mop_pad_cleaned` | Robot vacuum |

**Rule:** “Filter Changed” is not used in new templates. The canonical term is **Filter Replaced**. Existing Café entries keep `filter_changed`; new templates use `filter_replaced`.

---

## 4. Catalog

Legend: **Default** = single-scan action. **Pre-tick** = selected by default. **Quick** = one of the two action buttons in the double-scan notification. The third button is always **Open Appliance tasks**.

### Coffee Machine — `coffee_machine`

| Label | Key | How often | Default | Pre-tick | Quick |
|---|---|---|---:|---|---|
| Cleaned | `cleaned` | 1 week | ✓ | ✓ | — |
| Beans Refilled | `beans_refilled` | 4 days | | ✓ | ✓ |
| Descaled | `descaled` | 60 days | | ✓ | ✓ |
| Filter Replaced | `filter_replaced` | 90 days | | ✓ | — |
| Milk System Cleaned | `milk_system_cleaned` | 1 day | | ☐ | — |
| Water Tank Refilled | `water_tank_refilled` | 2 days | | ☐ | — |

**Pre-selected:** Cleaned, Beans Refilled, Descaled, Filter Replaced.
**Menu:** Beans Refilled · Descaled · Open Appliance tasks.

### Litter Box — `litter_box`

| Label | Key | How often | Default | Pre-tick | Quick |
|---|---|---|---:|---|---|
| Cleaned | `cleaned` | 1 day | ✓ | ✓ | — |
| Litter Replaced | `litter_replaced` | 30 days | | ✓ | ✓ |
| Deep Cleaned | `deep_cleaned` | 14 days | | ✓ | ✓ |
| Carbon Filter Replaced | `carbon_filter_replaced` | 30 days | | ☐ | — |
| Liner Replaced | `liner_replaced` | 14 days | | ☐ | — |
| Drawer Emptied | `drawer_emptied` | 3 days | | ☐ | — |

**Pre-selected:** Cleaned, Litter Replaced, Deep Cleaned.
**Menu:** Litter Replaced · Deep Cleaned · Open Appliance tasks.

### Pet Feeder — `pet_feeder`

| Label | Key | How often | Default | Pre-tick | Quick |
|---|---|---|---:|---|---|
| Cleaned | `cleaned` | 1 week | ✓ | ✓ | — |
| Food Refilled | `food_refilled` | 2 days | | ✓ | ✓ |
| Desiccant Replaced | `desiccant_replaced` | 30 days | | ✓ | ✓ |
| Battery Replaced | `battery_replaced` | 90 days | | ☐ | — |

**Pre-selected:** Cleaned, Food Refilled, Desiccant Replaced.
**Menu:** Food Refilled · Desiccant Replaced · Open Appliance tasks.

### Water Fountain — `water_fountain`

| Label | Key | How often | Default | Pre-tick | Quick |
|---|---|---|---:|---|---|
| Cleaned | `cleaned` | 1 week | ✓ | ✓ | — |
| Water Refilled | `water_refilled` | 2 days | | ✓ | ✓ |
| Filter Replaced | `filter_replaced` | 30 days | | ✓ | ✓ |
| Pump Cleaned | `pump_cleaned` | 30 days | | ☐ | — |

**Pre-selected:** Cleaned, Water Refilled, Filter Replaced.
**Menu:** Water Refilled · Filter Replaced · Open Appliance tasks.

### AC Unit — `ac_unit`

| Label | Key | How often | Default | Pre-tick | Quick |
|---|---|---|---:|---|---|
| Cleaned | `cleaned` | 30 days | ✓ | ✓ | — |
| Filter Replaced | `filter_replaced` | 180 days | | ✓ | ✓ |
| Deep Cleaned | `deep_cleaned` | 180 days | | ✓ | ✓ |
| Drain Line Flushed | `drain_line_flushed` | 180 days | | ☐ | — |
| Coils Cleaned | `coils_cleaned` | 180 days | | ☐ | — |
| Serviced | `serviced` | 180 days | | ☐ | — |

**Pre-selected:** Cleaned, Filter Replaced, Deep Cleaned.
**Menu:** Filter Replaced · Deep Cleaned · Open Appliance tasks.
**Note:** “Cleaned” here means clean the filter/unit. The help text should say “Clean the filter and front grille.”

### Guinea Pig Habitat — `guinea_pig_habitat`

| Label | Key | How often | Default | Pre-tick | Quick |
|---|---|---|---:|---|---|
| Cleaned | `cleaned` | 1 day | ✓ | ✓ | — |
| Hay Refilled | `hay_refilled` | 1 day | | ✓ | ✓ |
| Water Changed | `water_changed` | 1 day | | ✓ | ✓ |
| Bedding Replaced | `bedding_replaced` | 1 week | | ✓ | — |
| Deep Cleaned | `deep_cleaned` | 30 days | | ☐ | — |
| Nail Trimmed | `nail_trimmed` | 30 days | | ☐ | — |

**Pre-selected:** Cleaned, Hay Refilled, Water Changed, Bedding Replaced.
**Menu:** Hay Refilled · Water Changed · Open Appliance tasks.
**Note:** “Cleaned” means spot-clean the habitat. Nail trimming is pet care and should move to a future `small_pet_care` template.

### Robot Vacuum — `robot_vacuum` (proposed)

| Label | Key | How often | Default | Pre-tick | Quick |
|---|---|---|---:|---|---|
| Maintained | `maintained` | 1 week | ✓ | ✓ | — |
| Bag Emptied | `bag_emptied` | 3 days | | ✓ | ✓ |
| Filter Replaced | `filter_replaced` | 60 days | | ✓ | ✓ |
| Brush Replaced | `brush_replaced` | 90 days | | ✓ | — |
| Mop Pad Cleaned | `mop_pad_cleaned` | 1 week | | ☐ | — |
| Sensors Wiped | `sensors_wiped` | 1 week | | ☐ | — |

**Pre-selected:** Maintained, Bag Emptied, Filter Replaced, Brush Replaced.
**Menu:** Bag Emptied · Filter Replaced · Open Appliance tasks.
**Exception:** the robot vacuum’s cleaning equivalent is **Maintained**, because the appliance performs the cleaning. Confirm whether to keep that exception or add a `cleaned` action.

### Custom — `custom`

No preset actions. The existing action editor remains, with label-driven key generation and the same validation.

---

## 5. Notification menu contract

Current behavior sends every action, including the default. Android shows three. New behavior:

1. Exclude the default action.
2. Show **up to two quick actions** (template `quick` flag; fall back to catalog order if one is unticked).
3. Always append a third button:

```json
{
  "action": "URI",
  "title": "Open Appliance tasks",
  "uri": "/config/devices/device/<device_id>"
}
```

The Home Assistant Companion docs confirm Android opens a URI only when the action is `"URI"`, and a relative frontend path is supported. This gives a consistent three-button menu on Android and a gateway on iOS.

### What “Open Appliance tasks” should open

Recommended: the Home Assistant **device page** for that appliance, with one **button entity per action**:

```
button.cafe_cleaned
button.cafe_beans_refilled
button.cafe_descaled
button.cafe_filter_replaced
...
```

This requires adding per-action button entities (today there is only `button.<device>_log_manually`). Benefits:

- No generated dashboard or storage-mode dashboard writes.
- Works on Android and iOS with the standard Companion app.
- Every action is reachable from the device page.
- The same buttons are useful in dashboards and automations.

Alternative: a generated `nfc-tasgs` dashboard with one view per appliance. More work, more state to keep in sync. Start with the device page.

If the third button is tapped and the device page route is not reliable on a platform, fall back to opening the integration page or a persistent notification with all action buttons. Test on the Pixel before shipping.

---

## 6. Shopping and tasks (deferred)

**Decision:** no automatic shopping/task side effects from a scan or template action.

Current state to fix later:

- `triggers_purchase` adds `"<Label> (<Device>)"` to the shopping list when an action is logged. That is a chore name, not a product.
- `triggers_task` completes a matching task; the UI says “Creates a task.” The copy is wrong.

Future explicit model:

1. Each action may reference a **consumable** (`Coffee beans`, `Cat litter`).
2. A separate **Request supplies** button on the device page adds the consumable to the shopping list.
3. Only an explicit user action adds or completes a list item.
4. A “depleted” state can be added later, but it should be a user request, not inferred from a scan.

Not in v1. Existing entry-level flags stay for backward compatibility; templates do not expose them.

---

## 7. Use cases — the second layer

### The distinction

- **Appliance template** answers: *what is this object?* — Coffee Machine, Litter Box, AC Unit.
- **Use case** answers: *how is this particular object used?* — Espresso at home, Filter coffee at the office, Automatic litter box, Seasonal bedroom AC.

The same appliance needs different actions, defaults, and frequencies depending on use. A use case is a named selection of actions plus overrides; it does not duplicate the action definitions.

### Examples

| Appliance | Use case | What changes |
|---|---|---|
| Coffee Machine | Espresso — home | Cleaned weekly, Milk System Cleaned daily, Descaled every 60 days |
| Coffee Machine | Filter / drip — office | Cleaned weekly, Water Tank Refilled daily, Descaled quarterly, Filter Replaced quarterly |
| Litter Box | Manual | Cleaned daily, Deep Cleaned biweekly, Litter Replaced monthly |
| Litter Box | Automatic | Drawer Emptied every 3 days, Carbon Filter Replaced monthly, Deep Cleaned monthly |
| AC Unit | Home — seasonal | Cleaned monthly in season, Deep Cleaned yearly |
| AC Unit | Office — year-round | Cleaned monthly, Coils Cleaned quarterly |
| Guinea Pig Habitat | Single pig | Cleaned daily, Bedding Replaced weekly |
| Guinea Pig Habitat | Multi-pig / high traffic | Cleaned twice daily, Bedding Replaced twice weekly |

### Why not just more appliance templates?

That duplicates the action catalog and makes community review harder. A use case should be a small override layer:

```json
{
  "appliance": "coffee_machine",
  "use_case": "espresso_home",
  "name": "Espresso — home",
  "actions": [
    {"key": "cleaned", "enabled": true, "interval_hours": 168},
    {"key": "milk_system_cleaned", "enabled": true, "interval_hours": 24},
    {"key": "beans_refilled", "enabled": true, "interval_hours": 96},
    {"key": "descaled", "enabled": true, "interval_hours": 1440},
    {"key": "filter_replaced", "enabled": false}
  ],
  "default": "cleaned",
  "quick": ["beans_refilled", "milk_system_cleaned"]
}
```

### User-defined use cases

Later, after the core is stable:

- “Save this setup as a use case” on an existing device.
- Reuse it when adding another appliance of the same type.
- Edit the use case to update all devices that opted in, or fork it per device.

### Pipeline

1. Ship v1 with one generic appliance template per type (this document).
2. Add curated use cases for the highest-value appliances (espresso, automatic litter box, office AC).
3. Add user-defined use cases.
4. Keep `template_id` and optional `use_case_id` on the config entry; do not auto-rewrite actions when a template changes.

---

## 8. Validation rules

### Template/action validation

- At least one action; exactly one default.
- Default must be pre-ticked.
- Exactly two `quick` actions per template (or fewer, with fallback), never including the default.
- Keys unique within a template; match `^[a-z0-9_]+$`.
- Labels English, sentence case, past tense.
- Intervals shown in days/weeks/months; internally positive hours.
- No automatic shopping/task flags in template v1.
- `template_version` increments on additive changes.

### Parity with current test devices

| Device | Current | Template | Difference |
|---|---|---|---|
| Café | `cleaned`, `descaled`, `beans_refilled`, `filter_changed` | Coffee Machine | Template uses `filter_replaced`; existing keeps `filter_changed`. Default remains `cleaned`. |
| Caixa da Abby / Fritas | `cleaned`, `deep_cleaned`, `litter_replaced` | Litter Box | Matches. Default remains `cleaned`. |
| Robô da Abby / Fritas | `maintained`, `filter_replaced`, `brush_replaced`, `bag_emptied` | Robot Vacuum | Matches keys. Default remains `maintained` unless changed. |

No automatic migration. Templates apply to new entries; existing entries keep their actions and defaults.

---

## 9. Community PR rules

A new template PR includes:

- `id`, `name`, `icon`, `category`, description.
- Ordered actions with stable keys, English labels, “how often” values, one default, pre-tick flags, two quick flags.
- Rationale for the action set and intervals (manufacturer guidance or common practice).
- No brand names in IDs.
- No household-specific labels.
- JSON Schema validation + pytest catalog tests.
- CI checks: duplicate IDs/keys, missing default, invalid intervals, too many quick actions.
- Additive changes only; bump `template_version`.

---

## 10. Final decisions (locked)

1. **Robot vacuum:** `Maintained` stays the default. No extra `cleaned` action.
2. **Gateway target:** Home Assistant device page, with one `button.<device>_log_<action>` entity per action. No generated dashboard.
3. **Quick actions:** fixed two per template for now. Smart ranking by overdue/next-due can be considered later.
4. **iOS / Android:** same two quick actions + “Open Appliance tasks” third button on both platforms. Android gets a consistent 3-button menu; iOS can revisit later if desired.

## 11. Implementation status

Implemented on the test build (2026-10-19):

- `templates.py` catalog with seven appliance templates and stable keys.
- Config-flow steps: appliance picker → action checklist → preview/default.
- Template actions carry a `quick` flag; the catalog sets two per template.
- `build_menu_actions()` skips the default, chooses up to two quick actions, and appends the URI gateway.
- Per-action button entities (`button.<device>_log_<action>`) added for the device-page gateway.
- Entity `DeviceInfo` now uses the config-entry identifier instead of the device ID, preventing duplicate devices. Orphans left by the old build can be removed from the UI; the active device is protected.
- Tests: 21 passing in the HA 2026.10.2 container.
- Verified end-to-end on test HA: template flow, preview, per-action buttons, double-scan menu, gateway route.

Still pending: shipping this to live, cleaning up orphaned duplicate devices from the old build, and the future use-case layer.
