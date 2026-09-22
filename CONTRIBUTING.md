# Contributing

## Layout

The integration ships from `custom_components/nfc_tasgs/`. Everything else
(`tests/`, `docs/`, tooling) is development-only and is never copied to Home
Assistant.

## Workflow

1. Branch off `master`; never commit directly to it.
2. Keep commits small and use [Conventional Commits](https://www.conventionalcommits.org/)
   (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
3. Open a pull request. CI must pass (Hassfest, HACS, pytest).
4. No bug fix without a regression test.

## Local setup

```bash
python -m venv .venv
. .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements_test.txt
pre-commit install
```

## Checks

```bash
ruff check .        # lint
ruff format .       # format (or --check in CI)
pytest tests -q     # tests
```

## Versioning

Bump `version` in `custom_components/nfc_tasgs/manifest.json` and tag the release
`vX.Y.Z`. HACS reads versions from tags. Record the change in `CHANGELOG.md`.
