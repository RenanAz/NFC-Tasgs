# Agent notes — NFC Tasgs

Home Assistant custom integration. The integration lives in
`custom_components/nfc_tasgs/`; development files (`tests/`, `docs/`) are not
shipped.

## Before changing code

- Read `PRD.md` (what the code does today) and `docs/architecture.md` (module map).
- The current blocker and known defects are listed in `PRD.md` §8.

## Conventions

- One integration, one config entry per tracked "device"; actions are nested in the entry.
- Do not introduce YAML configuration for the integration.
- Keep Home Assistant API usage current with the pinned version in `requirements_test.txt`.
- Pure logic (interval math) must live outside `homeassistant` imports so it is unit-testable.

## Checks before opening a PR

```bash
ruff check .
ruff format --check .
pytest tests -q
```

## Rules

- Branch off `master`; never commit directly to it.
- Never commit secrets (tag IDs, tokens, personal data).
- Every bug fix ships with a regression test.
