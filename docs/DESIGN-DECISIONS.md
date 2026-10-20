# NFC Tasgs — Design Decisions

This is the running decision log for NFC Tasgs. Append new decisions at the top
of the table and add a detail section when a decision needs context. Use the
status values **Implemented**, **Deferred**, **Proposed**, or **Rejected**.

Related: [Appliance template catalog](TEMPLATE-CATALOG.md)

## Decision log

| Date | Area | Decision | Status |
|---|---|---|---|
| 2026-10-20 | Action keys | Custom action keys are derived from the label. Uppercase/accents are folded, spaces and punctuation become underscores, and duplicates get a numeric suffix. The key field is removed from the add/edit form. | Implemented |
| 2026-10-20 | Config flow | The Actions menu has a **Back** entry. Home Assistant does not support a native Back button on form steps; closing the dialog remains the cancel/back path from an add/edit form. | Implemented |
| 2026-10-20 | Tag picker | Tag selection uses a compact select dropdown instead of the full entity picker. | Implemented |
| 2026-10-19 | Templates | Appliance templates are the default add-device path; Custom remains available. | Implemented |
| 2026-10-19 | Notifications | Double-scan menu skips the default action, shows two fixed quick actions, and always ends with **Open Appliance tasks**. | Implemented |
| 2026-10-19 | Gateway | The notification gateway opens the HA device page; every action has `button.<device>_log_<action>`. | Implemented |
| 2026-10-19 | Intervals | Template intervals are seed values; self-learning takes over after two logs. No manual override yet. | Implemented |
| 2026-10-19 | Defaults | `Cleaned` is the default action where a template has a cleaning action; Robot Vacuum uses `Maintained`. | Implemented |
| 2026-10-19 | Shopping/tasks | Templates do not add shopping items or tasks automatically. Explicit consumable requests are deferred. | Deferred |
| 2026-10-19 | Use cases | A second layer of named use cases (espresso, automatic litter box, etc.) is planned after the core stabilizes. | Deferred |

---

## Deferred: editable interval number entities

**Status:** discussed, not implemented. The seed-only behavior stays for now.

The device page currently has no direct cadence control. The options flow does:
**Configure → Edit action → How often? (days)**. A number entity would make this
visible and automatable, but the semantics need to be explicit.

### Problem

An action has three interval concepts:

| Concept | Current source | Used by |
|---|---|---|
| Template seed | `expected_interval_hours` in the action config | First reminder before two scans |
| Learned interval | Measured average from scan history | `next_due` / `overdue` after two scans |
| Manual override | Not implemented | Would need to override both |

If a number entity edits only the seed, the user sets 7 days and the integration
ignores it after two scans. That is worse than the current options flow.

### Recommended shape (if implemented)

- `number.<device>_<action>_repeat_days` — “Repeat every”, unit **days**,
  `0.5–365`, step `0.5`, box mode.
- `button.<device>_<action>_reset_interval` — “Reset interval to automatic”.
- Number state is the effective interval: manual override if set, otherwise the
  learned interval, otherwise the template seed.
- Setting the number stores `manual_interval_hours` on the action.
- Reset clears the override and returns to learned/seed.
- Expose attributes: `source` (`manual`/`learned`/`template`),
  `manual_interval_days`, `learned_interval_days`, `template_interval_days`.

### Pros

- Direct edit from the device page and dashboards.
- Automatable with `number.set_value`.
- Visible current cadence.
- Template seeds remain useful starting points.
- No config-flow round trip for a routine tweak.

### Cons

- Two extra entities per action.
- Manual vs learned vs template must be explained clearly.
- Persistence and options-flow sync add complexity.
- Manual mode effectively pauses learning; users may forget they set it.
- Removed actions leave the number and reset button `unavailable`.
- Automations can accidentally change a cadence.

### Alternatives considered

| Option | Notes |
|---|---|
| Number + reset button | Recommended. Clearest; two extra entities per action. |
| One number, `0 = automatic` | Fewer entities, but “0 days = automatic” is not discoverable. |
| Number edits seed only | Rejected: breaks after two scans. |
| Options flow only | Current behavior; safe but buried. |

---

## Deferred: defer/snooze an overdue action

**Status:** discussed, not implemented. There is no snooze/defer behavior today.

### Current behavior

`nfc_tasgs.check_overdue` runs hourly. When an action is past `next_due`, it
sends a notification (24 h cooldown per action) and fires `nfc_tasgs_overdue`.
There is no way to postpone a single action without changing its interval or
logging a scan. Logging a scan is wrong when the filter still has 30% life; it
would pollute history and reset the learned interval.

### Proposed design

Add a service:

```yaml
action: nfc_tasgs.defer
data:
  device_id: <nfc_tasgs device>
  action_key: filter_replaced
  days: 15
```

Semantics:

- `deferred_until = max(now, next_due) + days`, so deferring never moves a due
  date earlier.
- Store `deferred_until_ts` per action in the existing `nfc_tasgs.history`
  store. It is a scheduling decision, not a scan.
- `next_due` reports the effective (deferred) date and exposes the original due
  date as an attribute.
- `binary_sensor.<action>_overdue` stays off until the defer expires.
- `check_overdue` skips deferred actions.
- Logging the action or calling `reset_action` clears the defer.
- Fire `nfc_tasgs_deferred` for automations.
- Deferring does not change `total_scans`, `first_scan_ts`, or the learned
  interval.

Initial UI: the service callable from Developer Tools, scripts, and dashboards.
Later, a dashboard shortcut or a per-action “Defer 15 days” button can call it.
Avoid adding a number entity per action just for defer; it would multiply the
entity count.

---

## Deferred: native Back button in config-flow forms

**Status:** limitation in Home Assistant core, not this integration.

Home Assistant config-flow forms expose only Submit; there is no per-step
`previous_step_id` API (see the upstream feature request, discussion #3134).
The workaround is a **Back** entry in the `async_show_menu` steps. The Actions
menu now has one. Add/edit/remove forms still have only Submit and the dialog’s
X; closing the dialog cancels the flow.

If HA adds native form back buttons, add `previous_step_id` to the action forms
and remove the workaround. Until then, do not add a boolean “Back” field to
forms: required-field validation prevents submitting a form with empty fields,
so the checkbox would not reliably work.

---

## Deferred: use-case layer

**Status:** designed, not implemented. See the template catalog for the model.

- Appliance template = what the object is (Coffee Machine).
- Use case = how this object is used (Espresso — home, Filter — office).
- A use case is a named selection of actions plus default/interval/quick
  overrides; it does not duplicate action definitions.
- Pipeline: generic templates → curated use cases → user-defined use cases.

---

## Deferred: shopping and task maturity

**Status:** current behavior retained; templates do not use the hooks.

- `triggers_purchase` currently adds `"<label> (<device>)"` to the shopping
  list when an action is logged. That is a chore name, not a product.
- `triggers_task` completes an existing matching task; the UI copy says
  “Creates a task”, which is wrong.
- Future design: an explicit **Request supplies** button per consumable, with
  `shopping_item` / `task_item` text. No automatic side effects from a scan.

---

## Rejected / not planned

- Deriving a released action key from a translated label at runtime.
- Auto-renaming existing action keys when a template changes.
- Editing a released template key in place; additive changes only, bump
  `template_version`.
- A generated dashboard for the notification gateway; the device page with
  per-action buttons is simpler and has no state to keep in sync.
