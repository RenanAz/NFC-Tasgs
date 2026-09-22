# Architecture

> Status: outline. Fill in as the module split (PRD §13, step 4) lands.

## Domain model

**Device → Action → Scan → DerivedStats**

- **Device** — one config entry; maps to one NFC tag and one physical object.
- **Action** — a named thing you do to the device (`cleaned`, `beans_refilled`).
- **Scan** — a logged occurrence (via NFC tag or manual `nfc_tasgs.log`).
- **DerivedStats** — computed from scan history: `interval_hours`, `next_due`, `overdue`.

## Modules

| Module | Responsibility |
|---|---|
| `custom_components/nfc_tasgs/__init__.py` | Entry setup/unload, platform forwarding |
| `.../helpers.py` | Pure interval math (no `homeassistant` imports) — *planned* |
| `.../coordinator.py` | Owns scan history + persistence — *planned* |
| `.../entity.py` | Base entity + dispatcher wiring — *planned* |
| `.../sensor.py` | Device-level and per-action sensors |
| `.../binary_sensor.py` | Per-action overdue binary sensor |
| `.../button.py` | Manual-log button |
| `.../services.py` | Service handlers (`scan`, `log`, `reset_action`, `set_assignee`) — *planned* |
| `.../config_flow.py` | UI config + options flow |
| `.../blueprints/tag_scan.yaml` | Scan → service automation |

## Data flow

NFC scan → `tag_scanned` event → blueprint → `nfc_tasgs.scan` → record scan →
persist history → refresh entities → fire `nfc_tasgs_action`.

## Decisions

Record architectural decisions as ADRs in `docs/adr/` (see `docs/adr/0001-*.md`).
