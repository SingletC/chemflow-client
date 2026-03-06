# Changelog

All notable changes to `chemflow-client` will be documented in this file.

## Unreleased

- Hardened `Chat3DWidget` message rendering to avoid executing HTML from user prompts or backend responses inside notebooks.
- Updated CI and contributor validation guidance to run the full test suite with notebook extras, and added Python 3.9 to the test matrix.

## 0.10

- Added `DEFAULT_BASE_URL` and made `https://chemcloud.info` the default SDK endpoint for public client entry points.
- Added click-to-toggle atom selection to `Chat3DWidget`, plus `get_selected_atom_indices()` and `clear_selection()`.
- Added an explicit notebook waiting state after `Send`, and changed widget request handling to surface failures in widget UI instead of raising by default.
- Changed widget `Send` handling to run in the background, and added `Chat3DWidget.chat_async(...)` so notebook cells can continue running while the request is in flight.
- Lowered the minimum supported Python version from 3.10 to 3.9.
- Changed the notebook waiting UX from a direct status banner to a chat-inline assistant thinking bubble.
- Added `CHEMFLOW_API_KEY` / `CHEMFLOW_BASE_URL` environment variable support across the public client entry points.
- Fixed notebook async chat completion so background results are scheduled back onto the Jupyter kernel loop instead of updating widget state from the worker thread.
- Allowed `ChemFlow3DClient.start()`, `Chat3DWidget()`, and one-shot `chat3d(atoms=None, ...)` to begin from an empty workspace and generate structure through chat.

## 0.1.0

- Initial public release.
- Added one-shot `chat3d(...)` API.
- Added stateful `ChemFlow3DClient` with one-step local undo.
- Added optional `Chat3DWidget` notebook cell widget.
