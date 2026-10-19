# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- HACS-compatible repository layout (`custom_components/nfc_tasgs/`).
- CI workflows: Hassfest and pytest.
- HACS validation is deferred until the integration is ready for publication.
- Developer tooling: ruff, pre-commit, and `pytest-homeassistant-custom-component`.
- Tests covering the integration manifest contract.

### Fixed

- Person resolution now matches the scanner's `device_tracker` against the
  `device_trackers` state attribute on `person` entities (works for YAML and
  storage persons), falling back to person registry options. Previously every
  scan resolved to "Unknown" on the live instance.
- Entity refresh signal is scoped per config entry instead of updating every
  NFC Tasgs entry on each scan.
- Timestamp sensors now return `datetime` values instead of ISO strings.
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
