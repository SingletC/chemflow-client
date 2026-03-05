# Release Process

## Prerequisites

- Clean git working tree
- PyPI token configured as `TWINE_PASSWORD`
- Username set to `__token__`

## Local Validation

```bash
python -m venv .venv
. .venv/bin/activate
pip install -U pip build twine pytest
pip install -e .[dev]
pytest
python -m build
python -m twine check dist/*
```

## Version Bump

1. Update `version` in `pyproject.toml`.
2. Add a new section to `CHANGELOG.md`.
3. Commit and tag: `git tag vX.Y.Z`.

## Publish

```bash
TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-token> python -m twine upload dist/*
```

## GitHub Release

- Push the version tag.
- The `publish.yml` workflow will build and publish from the tag if repository secrets are configured.
