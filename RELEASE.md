# Release Process

This repository publishes the `chemflow-client` package directly to PyPI.

## Prerequisites

- A clean git checkout based on the release commit you want to publish.
- PyPI project `chemflow-client` created on PyPI, or a pending Trusted Publisher configured for the first release.
- A GitHub environment named `pypi`.
- Trusted Publishing configured on PyPI for this GitHub repository.
- Optional but recommended: require manual approval on the `pypi` environment.

## Trusted Publishing Setup

Configure the following publisher in PyPI before the first release:

- Owner: `SingletC`
- Repository: `chemflow-client`
- Workflow filename: `publish.yml` (the workflow file is `.github/workflows/publish.yml`)
- Environment name: `pypi`

The workflow uses `pypa/gh-action-pypi-publish@release/v1` with GitHub OIDC. No long-lived API token is required after Trusted Publishing is configured.

## Local Validation

Run validation from a clean checkout. Do not publish from a working tree that contains local feature changes that are not part of the release.

If a local `build/` directory already exists in the repository root, it can shadow the installed `build` package and break `python -m build`. Remove local build artifacts first, or run the commands in a fresh clone.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev,notebook]
rm -rf build dist *.egg-info
pytest -q
python -m build
python -m twine check dist/*
```

## Versioning

For a new release:

1. Update `version` in `pyproject.toml`.
2. Promote the relevant notes from `CHANGELOG.md` into a new version section.
3. Commit the release changes.

For the first public release, keep the version at `0.1.0` unless release content changes.

## PyPI Release

After local validation succeeds:

```bash
git push origin dev
git tag v0.1.0
git push origin v0.1.0
```

Pushing the version tag triggers the `publish` workflow. The `build` and `publish-pypi` jobs will publish to PyPI.

## Post-release Checks

- Confirm the PyPI project page renders correctly.
- Install `chemflow-client==0.1.0` from PyPI in a clean virtual environment.
- Install `"chemflow-client[notebook]==0.1.0"` in a clean virtual environment.
- Verify `from chemflow_client import chat3d, ChemFlow3DClient, Chat3DWidget, DEFAULT_BASE_URL` succeeds.
- Verify the GitHub tag matches the released version.
