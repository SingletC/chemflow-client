# Changelog

All notable changes to `chemflow-client` will be documented in this file.

## Unreleased

- Added `DEFAULT_BASE_URL` and made `https://chemcloud.info` the default SDK endpoint for public client entry points.
- Added click-to-toggle atom selection to `Chat3DWidget`, plus `get_selected_atom_indices()` and `clear_selection()`.

## 0.1.0

- Initial public release.
- Added one-shot `chat3d(...)` API.
- Added stateful `ChemFlow3DClient` with one-step local undo.
- Added optional `Chat3DWidget` notebook cell widget.
