import importlib
import json
import sys
import threading
import time
import types

import pytest
import traitlets
from ase import Atoms

from chemflow_client.exceptions import ChemFlowHttpError
from chemflow_client.widget import (
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

    def fake_chat(_prompt):
        started.set()
        release.wait(1.0)
        updated = Atoms(symbols=["He"], positions=[[1.5, 0.0, 0.0]])
        widget._client._atoms = updated.copy()
        return updated, "Applied asynchronously."

    monkeypatch.setattr(widget._client, "chat", fake_chat)

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
