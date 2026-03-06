# Changelog

All notable changes to `chemflow-client` will be documented in this file.

## Unreleased

- Added `DEFAULT_BASE_URL` and made `https://chemcloud.info` the default SDK endpoint for public client entry points.
- Added click-to-toggle atom selection to `Chat3DWidget`, plus `get_selected_atom_indices()` and `clear_selection()`.
- Added an explicit notebook waiting state after `Send`, and changed widget request handling to surface failures in widget UI instead of raising by default.
- Changed widget `Send` handling to run in the background, and added `Chat3DWidget.chat_async(...)` so notebook cells can continue running while the request is in flight.
- Lowered the minimum supported Python version from 3.10 to 3.9.

## 0.1.0

- Initial public release.
- Added one-shot `chat3d(...)` API.
- Added stateful `ChemFlow3DClient` with one-step local undo.
- Added optional `Chat3DWidget` notebook cell widget.
