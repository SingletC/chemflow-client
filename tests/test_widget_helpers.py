import importlib
import json
import sys
import threading
import time
import types

import pytest
from ase import Atoms

traitlets = pytest.importorskip("traitlets", reason="widget tests require notebook extras")

from chemflow_client import CHEMFLOW_API_KEY_ENV_VAR, CHEMFLOW_BASE_URL_ENV_VAR
from chemflow_client.exceptions import ChemFlowHttpError
from chemflow_client.types import AtomsPayload, Chat3DResponse
from chemflow_client.widget import (
    _WIDGET_ESM,
    _format_widget_error_message,
    _normalize_selected_atom_indices,
    _toggle_selected_atom_index,
)


def test_normalize_selected_atom_indices_deduplicates_and_filters_invalid_values():
    normalized = _normalize_selected_atom_indices([2, 2, -1, 1, True, 7], max_atoms=4)

    assert normalized == [2, 1]


def test_toggle_selected_atom_index_matches_click_to_toggle_behavior():
    selected = _toggle_selected_atom_index([1, 3], atom_index=1, max_atoms=5)
    assert selected == [3]

    selected = _toggle_selected_atom_index(selected, atom_index=4, max_atoms=5)
    assert selected == [3, 4]


def test_format_widget_error_message_prefers_structured_message():
    error = ChemFlowHttpError(502, "upstream timeout")

    assert _format_widget_error_message(error) == "upstream timeout"


def test_widget_esm_uses_chat_thinking_placeholder_instead_of_waiting_banner():
    assert "Thinking..." in _WIDGET_ESM
    assert "Waiting for ChemFlow response:" not in _WIDGET_ESM


def test_widget_esm_keeps_fixed_shell_height_and_scrollable_message_area():
    assert 'height: min(720px, 78vh);' in _WIDGET_ESM
    assert 'overflow-y: auto;' in _WIDGET_ESM
    assert 'min-height: 0;' in _WIDGET_ESM


def test_widget_esm_renders_messages_via_text_nodes_instead_of_inner_html():
    assert "textEl.textContent = text;" in _WIDGET_ESM
    assert "roleEl.textContent = role;" in _WIDGET_ESM
    assert "messagesEl.replaceChildren(fragment);" in _WIDGET_ESM
    assert "messagesEl.innerHTML = buildMessageHtml(messages);" not in _WIDGET_ESM


def _reload_widget_module_with_fake_anywidget(monkeypatch):
    fake_module = types.ModuleType("anywidget")

    class FakeAnyWidget(traitlets.HasTraits):
        def on_msg(self, handler):
            self._message_handler = handler

    fake_module.AnyWidget = FakeAnyWidget
    monkeypatch.setitem(sys.modules, "anywidget", fake_module)

    import chemflow_client.widget as widget_module

    return importlib.reload(widget_module)


def test_widget_chat_handles_backend_errors_without_raising(monkeypatch):
    widget_module = _reload_widget_module_with_fake_anywidget(monkeypatch)
    widget = widget_module.Chat3DWidget(
        Atoms(symbols=["He"], positions=[[0.0, 0.0, 0.0]]),
        api_key="cfsk_test_key",
    )

    def fake_chat(_prompt):
        raise ChemFlowHttpError(503, "service unavailable")

    monkeypatch.setattr(widget._client, "chat", fake_chat)

    atoms, text = widget.chat("move it")

    assert text == ""
    assert atoms.get_chemical_symbols() == ["He"]
    assert widget.status_text == "Request failed"
    assert widget.error_text == "service unavailable"
    assert widget.busy is False
    assert widget.pending_prompt == ""

    messages = json.loads(widget.messages_json)
    assert messages[0] == {"role": "user", "text": "move it"}
    assert messages[1] == {"role": "system", "text": "Request failed: service unavailable"}


def test_widget_chat_can_still_raise_when_requested(monkeypatch):
    widget_module = _reload_widget_module_with_fake_anywidget(monkeypatch)
    widget = widget_module.Chat3DWidget(
        Atoms(symbols=["He"], positions=[[0.0, 0.0, 0.0]]),
        api_key="cfsk_test_key",
    )

    def fake_chat(_prompt):
        raise ChemFlowHttpError(504, "gateway timeout")

    monkeypatch.setattr(widget._client, "chat", fake_chat)

    with pytest.raises(ChemFlowHttpError):
        widget.chat("move it", raise_errors=True)


def test_widget_chat_async_returns_immediately_and_applies_result(monkeypatch):
    widget_module = _reload_widget_module_with_fake_anywidget(monkeypatch)
    widget = widget_module.Chat3DWidget(
        Atoms(symbols=["He"], positions=[[0.0, 0.0, 0.0]]),
        api_key="cfsk_test_key",
    )

    started = threading.Event()
    release = threading.Event()

    def fake_chat3d(_request):
        started.set()
        release.wait(1.0)
        return Chat3DResponse(
            session_id="sess-1",
            assistant_message="Applied asynchronously.",
            atoms=AtomsPayload(
                symbols=["He"],
                positions=[[1.5, 0.0, 0.0]],
            ),
            changed=True,
        )

    monkeypatch.setattr(widget._client._api, "chat3d", fake_chat3d)

    scheduled = widget.chat_async("move it async")

    assert scheduled is True
    assert widget.busy is True
    assert widget.pending_prompt == "move it async"
    assert started.wait(0.2)

    release.set()
    deadline = time.time() + 1.0
    while widget.busy and time.time() < deadline:
        time.sleep(0.01)

    assert widget.busy is False
    assert widget.pending_prompt == ""
    assert widget.status_text == "Ready"
    assert "Applied asynchronously." in widget.messages_json


def test_widget_chat_async_keeps_state_reads_and_close_responsive(monkeypatch):
    widget_module = _reload_widget_module_with_fake_anywidget(monkeypatch)
    widget = widget_module.Chat3DWidget(
        Atoms(symbols=["He"], positions=[[0.0, 0.0, 0.0]]),
        api_key="cfsk_test_key",
    )

    started = threading.Event()
    release = threading.Event()

    def fake_chat3d(_request):
        started.set()
        release.wait(1.0)
        return Chat3DResponse(
            session_id="sess-2",
            assistant_message="Applied asynchronously.",
            atoms=AtomsPayload(
                symbols=["He"],
                positions=[[2.0, 0.0, 0.0]],
            ),
            changed=True,
        )

    monkeypatch.setattr(widget._client._api, "chat3d", fake_chat3d)

    assert widget.chat_async("move it async") is True
    assert started.wait(0.2)

    read_started = time.perf_counter()
    atoms = widget.get_atoms()
    read_elapsed = time.perf_counter() - read_started

    close_started = time.perf_counter()
    widget.close()
    close_elapsed = time.perf_counter() - close_started

    assert atoms.get_chemical_symbols() == ["He"]
    assert read_elapsed < 0.1
    assert close_elapsed < 0.1

    release.set()
    deadline = time.time() + 1.0
    while widget._worker_thread is not None and time.time() < deadline:
        time.sleep(0.01)

    assert widget._worker_thread is None


def test_widget_can_initialize_empty_workspace(monkeypatch):
    widget_module = _reload_widget_module_with_fake_anywidget(monkeypatch)
    widget = widget_module.Chat3DWidget(api_key="cfsk_test_key")

    try:
        assert len(widget.get_atoms()) == 0
        assert widget.xyz_text == ""
        assert widget.status_text == "Ready"
    finally:
        widget.close()


def test_widget_can_generate_from_empty_workspace(monkeypatch):
    widget_module = _reload_widget_module_with_fake_anywidget(monkeypatch)
    widget = widget_module.Chat3DWidget(api_key="cfsk_test_key")

    def fake_chat(_prompt):
        updated = Atoms(symbols=["He"], positions=[[0.0, 0.0, 0.0]])
        widget._client._atoms = updated.copy()
        return updated, "Generated helium."

    monkeypatch.setattr(widget._client, "chat", fake_chat)

    atoms, text = widget.chat("generate helium")

    try:
        assert atoms.get_chemical_symbols() == ["He"]
        assert text == "Generated helium."
        assert widget.xyz_text.startswith("1\nChemFlow Client\nHe ")
    finally:
        widget.close()


def test_widget_can_resolve_configuration_from_environment(monkeypatch):
    widget_module = _reload_widget_module_with_fake_anywidget(monkeypatch)
    monkeypatch.setenv(CHEMFLOW_API_KEY_ENV_VAR, "cfsk_env_key")
    monkeypatch.setenv(CHEMFLOW_BASE_URL_ENV_VAR, "http://env.example:8000/")

    widget = widget_module.Chat3DWidget(Atoms(symbols=["He"], positions=[[0.0, 0.0, 0.0]]))

    try:
        assert str(widget._client._api._client.base_url).rstrip("/") == "http://env.example:8000"
        assert widget._client._api._client.headers["X-ChemFlow-Api-Key"] == "cfsk_env_key"
    finally:
        widget.close()


def test_widget_run_on_main_thread_uses_stored_kernel_io_loop(monkeypatch):
    widget_module = _reload_widget_module_with_fake_anywidget(monkeypatch)
    widget = widget_module.Chat3DWidget(
        Atoms(symbols=["He"], positions=[[0.0, 0.0, 0.0]]),
        api_key="cfsk_test_key",
    )

    callbacks = []
    invoked = []

    class FakeIOLoop:
        def add_callback(self, callback):
            callbacks.append(callback)

    widget._main_loop = None
    widget._kernel_io_loop = FakeIOLoop()

    worker = threading.Thread(
        target=lambda: widget._run_on_main_thread(lambda: invoked.append("done")),
        daemon=True,
    )
    worker.start()
    worker.join(timeout=1.0)

    assert invoked == []
    assert len(callbacks) == 1

    callbacks[0]()
    assert invoked == ["done"]

    widget.close()
