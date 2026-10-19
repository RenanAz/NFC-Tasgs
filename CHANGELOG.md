# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Tag picker in the config flow: tags are selected by name from Home
  Assistant's tag registry instead of pasting a UUID. If no tags exist, the
  flow explains how to create one first.
- Automatic `tag_scanned` handling: the integration resolves its own tags and
  starts the scan flow directly. Can be disabled per device with `auto_scan`.
- Double-scan detection in the integration (`double_scan_window_seconds`):
  a single scan logs the default action after the window; a second scan sends
  an actionable notification menu to the scanning phone.
- `notify_service` option (e.g. `mobile_app_your_phone`) for the action menu;
  it is auto-resolved from the scanner's device when possible.
- Overdue reminders: an hourly check sends a notification for each overdue
  action (at most once per 24 h) and fires `nfc_tasgs_overdue`. Also exposed as
  the `nfc_tasgs.check_overdue` service for manual runs.
- Shopping-list hook: actions with `triggers_purchase` add a deduplicated item
  to the device's shopping list.
- Task-list hook: actions with `triggers_task` complete a matching open item in
  the device's task list.
- Overdue notifications fall back to the assignee's or owners' phone when the
  device has no explicit notify service.
- Structured action editor in the config and options flows: add, edit, and
  remove actions with key, label, expected interval, and purchase/task flags.
- Appliance templates: a new device can start from a curated preset (Coffee
  Machine, Litter Box, Pet Feeder, Water Fountain, AC Unit, Guinea Pig Habitat,
  Robot Vacuum) with pre-ticked actions and a live entity preview. Keys come
  from the catalog; custom actions still use label-driven keys.
- Per-action button entities (`button.<device>_log_<action>`) so every action
  is reachable from the appliance's device page.
- Double-scan menus now show two quick action buttons plus an
  “Open Appliance tasks” URI button that opens the device page. The default
  action is omitted from the menu.
- Device options now use Home Assistant selectors: owners/assignee (person),
  notification target (notify), task/shopping lists (todo), icon, and area.
  New optional `notify_entity` option.
- HACS-compatible repository layout (`custom_components/nfc_tasgs/`).
- CI workflows: Hassfest and pytest.
- HACS validation is deferred until the integration is ready for publication.
- Developer tooling: ruff, pre-commit, and `pytest-homeassistant-custom-component`.
- Tests covering the integration manifest contract.

### Removed

- The tag-scan blueprint and its external helper dependency (`input_text`/`timer`).
- `notify_entity` option (replaced by `notify_service`).

### Fixed

- Options flow no longer assigns `self.config_entry` in `__init__` (unsupported
  since HA 2024.11), so device options are configurable again.
- Entities now attach to the config-entry device instead of creating a second
  device from the virtual device ID. This removes the duplicate-device pairs
  seen on upgraded installs; previously created orphans can be deleted from
  the device registry after the upgrade.
- `nfc_tasgs.set_assignee` now persists the change to the config entry and
  refreshes entities.
- Person resolution now matches the scanner's `device_tracker` against the
  `device_trackers` state attribute on `person` entities (works for YAML and
  storage persons), falling back to person registry options. Previously every
  scan resolved to "Unknown" on the live instance.
- Entity refresh signal is scoped per config entry instead of updating every
  NFC Tasgs entry on each scan.
- Timestamp sensors now return `datetime` values instead of ISO strings.
- `next_due` is now unknown until an action has been scanned at least once
  (previously the seed produced a fresh `now + interval` date on every restart).
- Entity unique IDs are now scoped to the config entry (existing entities are
  migrated on setup), so two devices with the same name no longer collide.
- Action keys are normalized to lowercase; the config flow rejects duplicates
  and invalid keys instead of silently dropping them.
- `binary_sensor.py` syntax error that blocked integration setup (`setup_error`) and
  crashed Hassfest.

### Security

- Replaced example NFC tag IDs, person entity IDs and device IDs in the docs and
  service definitions with non-real placeholders.
- GitHub Actions are pinned to commit SHAs and limited to `contents: read`; added
  Dependabot configuration for `github-actions`.

## [0.1.0]

Initial implementation: config flow, per-device and per-action sensors, overdue
binary sensor, manual-log button, four services, self-learning interval math,
storage persistence, and a tag-scan automation blueprint.
