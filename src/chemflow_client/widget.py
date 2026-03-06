"""Notebook widget for ChemFlow 3D chat."""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Optional, Tuple, Union

from ase import Atoms

from .ase_adapter import AseAtomsAdapter
from .client import ChemFlow3DClient
from .constants import DEFAULT_BASE_URL
from .exceptions import ChemFlowError

try:
    import anywidget
    import traitlets
except ImportError:  # pragma: no cover - optional dependency path
    anywidget = None
    traitlets = None


def _normalize_selected_atom_indices(values: list[int], max_atoms: int) -> list[int]:
    if max_atoms <= 0:
        return []

    normalized: list[int] = []
    seen: set[int] = set()
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int):
            continue
        if value < 0 or value >= max_atoms or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _toggle_selected_atom_index(values: list[int], atom_index: int, max_atoms: int) -> list[int]:
    normalized = _normalize_selected_atom_indices(values, max_atoms)
    if atom_index < 0 or atom_index >= max_atoms:
        return normalized
    if atom_index in normalized:
        return [value for value in normalized if value != atom_index]
    return [*normalized, atom_index]


def _format_widget_error_message(error: Union[Exception, str]) -> str:
    if isinstance(error, str):
        message = error
    elif isinstance(error, ChemFlowError):
        message = getattr(error, "message", "") or str(error)
    else:
        message = str(error)

    normalized = (message or "").strip()
    if normalized:
        return normalized
    if isinstance(error, Exception):
        return error.__class__.__name__
    return "Request failed"


_WIDGET_ESM = r'''
const THREE_DMOL_URL = "https://cdn.jsdelivr.net/npm/3dmol@2.4.2/build/3Dmol-min.js";

async function ensure3Dmol() {
  if (window.$3Dmol) {
    return window.$3Dmol;
  }
  await new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = THREE_DMOL_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load 3Dmol.js"));
    document.head.appendChild(script);
  });
  return window.$3Dmol;
}

function parseMessages(rawValue) {
  try {
    return JSON.parse(rawValue || "[]");
  } catch {
    return [];
  }
}

function parseSelectedAtomIndices(rawValue) {
  try {
    const values = JSON.parse(rawValue || "[]");
    if (!Array.isArray(values)) {
      return [];
    }
    return values.filter((value) => Number.isInteger(value) && value >= 0);
  } catch {
    return [];
  }
}

function buildMessageHtml(messages) {
  return messages.map((entry) => {
    const role = entry.role || "assistant";
    const text = entry.text || "";
    return `<div class="cf-msg cf-msg-${role}"><div class="cf-role">${role}</div><div class="cf-text">${text}</div></div>`;
  }).join("");
}

function readAtomIntegerField(atom, field) {
  const value = atom?.[field];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return null;
  }
  return Math.trunc(value);
}

function resolveAtomIndexFrom3Dmol(atom, maxAtoms) {
  if (!Number.isInteger(maxAtoms) || maxAtoms <= 0) {
    return -1;
  }

  const index = readAtomIntegerField(atom, "index");
  if (index !== null && index >= 0 && index < maxAtoms) {
    return index;
  }

  const serial = readAtomIntegerField(atom, "serial");
  if (serial === null) {
    return -1;
  }

  const oneBased = serial - 1;
  if (oneBased >= 0 && oneBased < maxAtoms) {
    return oneBased;
  }

  const serialBase = atom?.serialBase;
  const serialIsExplicitZeroBased = serial === 0 || serialBase === 0;
  if (!serialIsExplicitZeroBased) {
    return -1;
  }

  if (serial >= 0 && serial < maxAtoms) {
    return serial;
  }

  return -1;
}

function getAtomCountFromXyz(xyzText) {
  const firstLine = (xyzText || "").split(/\r?\n/, 1)[0]?.trim() || "";
  const atomCount = Number.parseInt(firstLine, 10);
  return Number.isInteger(atomCount) && atomCount > 0 ? atomCount : 0;
}

function getBaseStyle() {
  return {
    stick: { radius: 0.16 },
    sphere: { scale: 0.28 },
  };
}

function getSelectionStyle() {
  return {
    stick: { radius: 0.16 },
    sphere: { scale: 0.35, color: "#fff59d", opacity: 1 },
  };
}

function render({ model, el }) {
  el.innerHTML = `
    <div class="cf-shell">
      <style>
        .cf-shell { font-family: Georgia, serif; color: #192126; background: linear-gradient(180deg, #f8f5ee, #efe8da); border: 1px solid #c8bba6; border-radius: 18px; overflow: hidden; }
        .cf-grid { display: grid; grid-template-columns: minmax(320px, 1.3fr) minmax(280px, 1fr); min-height: 420px; }
        .cf-viewer { min-height: 420px; background: radial-gradient(circle at top, #ffffff, #ece4d5); }
        .cf-side { display: flex; flex-direction: column; border-left: 1px solid #d8ccb7; }
        .cf-status { padding: 12px 14px; font-size: 13px; letter-spacing: 0.02em; border-bottom: 1px solid #d8ccb7; background: rgba(255,255,255,0.55); }
        .cf-status[data-error="true"] { color: #9d2d20; }
        .cf-waiting { display: none; align-items: center; gap: 10px; padding: 10px 14px; border-bottom: 1px solid #d8ccb7; background: rgba(29,92,99,0.08); color: #1d5c63; }
        .cf-waiting[data-busy="true"] { display: flex; }
        .cf-spinner { width: 14px; height: 14px; border-radius: 999px; border: 2px solid rgba(29,92,99,0.18); border-top-color: #1d5c63; animation: cf-spin 0.9s linear infinite; flex: 0 0 auto; }
        .cf-waiting-text { font-size: 12px; line-height: 1.4; }
        .cf-selection { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 14px; border-bottom: 1px solid #d8ccb7; background: rgba(255,255,255,0.42); }
        .cf-selection-text { font-size: 12px; line-height: 1.4; color: #334047; }
        .cf-selection-clear { border: 0; border-radius: 999px; padding: 6px 10px; cursor: pointer; background: #d9c7a5; color: #3b2e18; font-size: 12px; }
        .cf-selection-clear:disabled { cursor: default; opacity: 0.45; }
        .cf-messages { flex: 1; overflow: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
        .cf-msg { padding: 10px 12px; border-radius: 12px; border: 1px solid #d7c6ab; background: rgba(255,255,255,0.8); }
        .cf-msg-user { background: #dfe9f3; border-color: #b8cadb; }
        .cf-msg-system { background: #efe6d6; border-color: #d8c8ad; }
        .cf-role { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; margin-bottom: 4px; }
        .cf-text { white-space: pre-wrap; line-height: 1.4; }
        .cf-form { display: flex; gap: 10px; padding: 14px; border-top: 1px solid #d8ccb7; background: rgba(255,255,255,0.62); }
        .cf-input { flex: 1; border: 1px solid #b8aa91; border-radius: 10px; padding: 10px 12px; background: #fffdf8; }
        .cf-button { border: 0; border-radius: 10px; padding: 10px 14px; cursor: pointer; background: #1d5c63; color: white; }
        .cf-button:disabled, .cf-input:disabled { cursor: default; opacity: 0.6; }
        .cf-button-secondary { background: #8c6b3f; }
        @keyframes cf-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @media (max-width: 860px) {
          .cf-grid { grid-template-columns: 1fr; }
          .cf-side { border-left: 0; border-top: 1px solid #d8ccb7; }
        }
      </style>
      <div class="cf-grid">
        <div class="cf-viewer"></div>
        <div class="cf-side">
          <div class="cf-status"></div>
          <div class="cf-waiting" data-busy="false">
            <div class="cf-spinner"></div>
            <div class="cf-waiting-text"></div>
          </div>
          <div class="cf-selection">
            <div class="cf-selection-text"></div>
            <button class="cf-selection-clear" type="button">Clear</button>
          </div>
          <div class="cf-messages"></div>
          <form class="cf-form">
            <input class="cf-input" type="text" placeholder="Describe the structural edit" />
            <button class="cf-button cf-button-send" type="submit">Send</button>
            <button class="cf-button cf-button-secondary" type="button">Undo</button>
          </form>
        </div>
      </div>
    </div>
  `;

  const viewerEl = el.querySelector(".cf-viewer");
  const statusEl = el.querySelector(".cf-status");
  const waitingEl = el.querySelector(".cf-waiting");
  const waitingTextEl = el.querySelector(".cf-waiting-text");
  const selectionEl = el.querySelector(".cf-selection-text");
  const clearSelectionButton = el.querySelector(".cf-selection-clear");
  const messagesEl = el.querySelector(".cf-messages");
  const formEl = el.querySelector(".cf-form");
  const inputEl = el.querySelector(".cf-input");
  const sendButton = el.querySelector(".cf-button-send");
  const undoButton = el.querySelector(".cf-button-secondary");
  let viewer = null;
  let currentModel = null;
  let currentXyzText = "";
  let optimisticBusy = false;
  let optimisticPrompt = "";
  let disposed = false;

  async function syncViewer() {
    const xyzText = model.get("xyz_text") || "";
    const $3Dmol = await ensure3Dmol();
    if (disposed) {
      return;
    }

    if (!viewer) {
      viewer = $3Dmol.createViewer(viewerEl, { backgroundColor: "#f7f2e8" });
    }

    if (xyzText !== currentXyzText) {
      currentXyzText = xyzText;
      currentModel = null;
      viewer.clear();

      if (xyzText.trim()) {
        currentModel = viewer.addModel(xyzText, "xyz");
        viewer.setClickable({}, true, (atom) => {
          const atomIndex = resolveAtomIndexFrom3Dmol(atom, getAtomCountFromXyz(currentXyzText));
          if (atomIndex >= 0) {
            model.send({ type: "toggle_selection", atom_index: atomIndex });
          }
        });
        currentModel.setStyle({}, getBaseStyle());
        viewer.zoomTo();
      }
    }

    if (currentModel) {
      currentModel.setStyle({}, getBaseStyle());
      parseSelectedAtomIndices(model.get("selected_atom_indices_json")).forEach((index) => {
        currentModel.setStyle({ index }, getSelectionStyle());
      });
    }

    viewer.render();
  }

  function renderMessages() {
    const messages = parseMessages(model.get("messages_json"));
    messagesEl.innerHTML = buildMessageHtml(messages);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function renderSelection() {
    const selected = parseSelectedAtomIndices(model.get("selected_atom_indices_json"));
    const busy = optimisticBusy || Boolean(model.get("busy"));
    if (selected.length === 0) {
      selectionEl.textContent = "Selected atoms: none";
      clearSelectionButton.disabled = true;
      return;
    }

    selectionEl.textContent = `Selected atoms (${selected.length}): ${selected.map((index) => index + 1).join(", ")}`;
    clearSelectionButton.disabled = busy;
  }

  function renderStatus() {
    const errorText = model.get("error_text") || "";
    const statusText = model.get("status_text") || "Ready";
    statusEl.dataset.error = errorText ? "true" : "false";
    statusEl.textContent = errorText || statusText;
  }

  function renderBusyState() {
    const busy = optimisticBusy || Boolean(model.get("busy"));
    const pendingPrompt = (model.get("pending_prompt") || optimisticPrompt || "").trim();

    inputEl.disabled = busy;
    sendButton.disabled = busy;
    sendButton.textContent = busy ? "Waiting..." : "Send";
    undoButton.disabled = busy;

    waitingEl.dataset.busy = busy ? "true" : "false";
    waitingTextEl.textContent = pendingPrompt
      ? `Waiting for ChemFlow response: ${pendingPrompt}`
      : "Waiting for ChemFlow response...";

    renderSelection();
  }

  function handleResize() {
    if (!viewer) {
      return;
    }
    viewer.resize();
    viewer.render();
  }

  formEl.addEventListener("submit", (event) => {
    event.preventDefault();
    const prompt = (inputEl.value || "").trim();
    if (!prompt) {
      return;
    }
    optimisticBusy = true;
    optimisticPrompt = prompt;
    renderBusyState();
    inputEl.value = "";
    model.send({ type: "chat", prompt });
  });

  undoButton.addEventListener("click", () => {
    model.send({ type: "undo" });
  });

  clearSelectionButton.addEventListener("click", () => {
    model.send({ type: "clear_selection" });
  });

  window.addEventListener("resize", handleResize);

  model.on("change:busy", () => {
    const busy = Boolean(model.get("busy"));
    optimisticBusy = busy;
    if (!busy) {
      optimisticPrompt = "";
    }
    renderBusyState();
  });
  model.on("change:pending_prompt", renderBusyState);
  model.on("change:xyz_text", syncViewer);
  model.on("change:selected_atom_indices_json", syncViewer);
  model.on("change:selected_atom_indices_json", renderSelection);
  model.on("change:messages_json", renderMessages);
  model.on("change:status_text", renderStatus);
  model.on("change:error_text", renderStatus);

  syncViewer();
  renderBusyState();
  renderSelection();
  renderMessages();
  renderStatus();

  return () => {
    disposed = true;
    window.removeEventListener("resize", handleResize);
  };
}

export default { render };
'''


if anywidget is None or traitlets is None:  # pragma: no cover - optional dependency path
    class Chat3DWidget:
        """Placeholder widget class when notebook extras are not installed."""

        def __init__(self, *args, **kwargs) -> None:
            raise ImportError(
                "Chat3DWidget requires optional notebook dependencies. "
                'Install with `pip install "chemflow-client[notebook]"`.'
            )
else:
    class Chat3DWidget(anywidget.AnyWidget):
        """Notebook cell widget for ChemFlow 3D editing."""

        _esm = _WIDGET_ESM
        xyz_text = traitlets.Unicode("").tag(sync=True)
        messages_json = traitlets.Unicode("[]").tag(sync=True)
        status_text = traitlets.Unicode("Ready").tag(sync=True)
        error_text = traitlets.Unicode("").tag(sync=True)
        busy = traitlets.Bool(False).tag(sync=True)
        pending_prompt = traitlets.Unicode("").tag(sync=True)
        selected_atom_indices_json = traitlets.Unicode("[]").tag(sync=True)

        def __init__(
            self,
            atoms: Atoms,
            *,
            base_url: str = DEFAULT_BASE_URL,
            api_key: str,
            model: Optional[str] = None,
            timeout: float = 300.0,
        ) -> None:
            super().__init__()
            self._client_lock = threading.RLock()
            self._main_thread = threading.current_thread()
            self._worker_thread: Optional[threading.Thread] = None
            self._closed = False
            try:
                self._main_loop = asyncio.get_running_loop()
            except RuntimeError:
                self._main_loop = None
            self._client = ChemFlow3DClient(
                base_url=base_url,
                api_key=api_key,
                model=model,
                timeout=timeout,
            )
            with self._client_lock:
                self._client.start(atoms)
            self._messages: list[dict[str, str]] = []
            self._selected_atom_indices: list[int] = []
            self._sync_xyz(self.get_atoms())
            self._sync_selection()
            self.on_msg(self._handle_frontend_message)

        def _sync_xyz(self, atoms: Atoms) -> None:
            self.xyz_text = AseAtomsAdapter.to_xyz_text(atoms)

        def _sync_messages(self) -> None:
            self.messages_json = json.dumps(self._messages)

        def _sync_selection(self) -> None:
            self.selected_atom_indices_json = json.dumps(self._selected_atom_indices)

        def _set_busy_state(self, is_busy: bool, pending_prompt: str = "") -> None:
            self.busy = bool(is_busy)
            self.pending_prompt = pending_prompt if is_busy else ""

        def _run_on_main_thread(self, callback) -> None:
            if self._closed:
                return
            if threading.current_thread() is self._main_thread:
                callback()
                return

            if self._main_loop is not None:
                try:
                    self._main_loop.call_soon_threadsafe(callback)
                    return
                except RuntimeError:
                    pass

            try:
                from IPython import get_ipython

                ip = get_ipython()
                kernel = getattr(ip, "kernel", None)
                io_loop = getattr(kernel, "io_loop", None)
                if io_loop is not None:
                    io_loop.add_callback(callback)
                    return
            except Exception:
                pass

            callback()

        def _append_message(self, role: str, text: str) -> None:
            normalized_text = (text or "").strip()
            if not normalized_text:
                return
            self._messages.append({"role": role, "text": normalized_text})
            self._sync_messages()

        def _set_error_state(
            self,
            error: Union[Exception, str],
            *,
            append_message: bool = True,
            clear_busy: bool = True,
            status: str = "Request failed",
        ) -> str:
            message = _format_widget_error_message(error)
            if clear_busy:
                self._set_busy_state(False)
            self.status_text = status
            self.error_text = message
            if append_message:
                self._append_message("system", f"Request failed: {message}")
            return message

        def _clear_selection_state(self) -> None:
            self._selected_atom_indices = []
            self._sync_selection()

        def _toggle_selection_state(self, atom_index: int) -> list[int]:
            atom_count = len(self.get_atoms())
            self._selected_atom_indices = _toggle_selected_atom_index(
                self._selected_atom_indices,
                atom_index,
                atom_count,
            )
            self._sync_selection()
            return self.get_selected_atom_indices()

        def _finalize_background_chat_success(self, atoms: Atoms, text: str) -> None:
            self._worker_thread = None
            if self._closed:
                return
            self._append_message("assistant", text)
            self._sync_xyz(atoms)
            self._clear_selection_state()
            self._set_busy_state(False)
            self.error_text = ""
            self.status_text = "Ready"

        def _finalize_background_chat_error(self, exc: Exception) -> None:
            self._worker_thread = None
            if self._closed:
                return
            self._set_error_state(exc)

        def _background_chat_worker(self, prompt: str) -> None:
            try:
                with self._client_lock:
                    atoms, text = self._client.chat(prompt)
            except Exception as exc:
                self._run_on_main_thread(lambda exc=exc: self._finalize_background_chat_error(exc))
                return

            self._run_on_main_thread(lambda atoms=atoms, text=text: self._finalize_background_chat_success(atoms, text))

        def chat_async(self, prompt: str, *, raise_errors: bool = False) -> bool:
            normalized_prompt = (prompt or "").strip()
            if not normalized_prompt:
                message = self._set_error_state("prompt is required", append_message=False, clear_busy=False)
                if raise_errors:
                    raise ValueError(message)
                return False

            if self.busy:
                message = self._set_error_state(
                    "Another request is already in progress.",
                    append_message=False,
                    clear_busy=False,
                    status="Busy",
                )
                if raise_errors:
                    raise RuntimeError(message)
                return False

            self.error_text = ""
            self.status_text = "Waiting for ChemFlow response..."
            self._set_busy_state(True, normalized_prompt)
            self._append_message("user", normalized_prompt)

            try:
                worker = threading.Thread(
                    target=self._background_chat_worker,
                    args=(normalized_prompt,),
                    name="chemflow-widget-chat",
                    daemon=True,
                )
                self._worker_thread = worker
                worker.start()
            except Exception as exc:
                self._worker_thread = None
                self._set_error_state(exc)
                if raise_errors:
                    raise
                return False

            return True

        def _handle_frontend_message(self, _, content, buffers) -> None:
            del buffers
            message_type = (content or {}).get("type")
            try:
                if message_type == "chat":
                    self.chat_async(str((content or {}).get("prompt") or ""))
                    return
                if message_type == "undo":
                    self.undo()
                    return
                if message_type == "toggle_selection":
                    if self.busy:
                        return
                    atom_index = int((content or {}).get("atom_index"))
                    self._toggle_selection_state(atom_index)
                    return
                if message_type == "clear_selection":
                    if self.busy:
                        return
                    self.clear_selection()
                    return
            except Exception as exc:
                self._set_error_state(exc)

        def chat(self, prompt: str, *, raise_errors: bool = False) -> Tuple[Atoms, str]:
            normalized_prompt = (prompt or "").strip()
            if not normalized_prompt:
                message = self._set_error_state("prompt is required", append_message=False, clear_busy=False)
                if raise_errors:
                    raise ValueError(message)
                return self.get_atoms(), ""
            if self.busy:
                message = self._set_error_state(
                    "Another request is already in progress.",
                    append_message=False,
                    clear_busy=False,
                    status="Busy",
                )
                if raise_errors:
                    raise RuntimeError(message)
                return self.get_atoms(), ""
            self.error_text = ""
            self.status_text = "Waiting for ChemFlow response..."
            self._set_busy_state(True, normalized_prompt)
            self._append_message("user", normalized_prompt)

            try:
                with self._client_lock:
                    atoms, text = self._client.chat(normalized_prompt)
            except Exception as exc:
                self._set_error_state(exc)
                if raise_errors:
                    raise
                return self.get_atoms(), ""

            self._append_message("assistant", text)
            self._sync_xyz(atoms)
            self._clear_selection_state()
            self._set_busy_state(False)
            self.status_text = "Ready"
            return self.get_atoms(), text

        def set_atoms(self, atoms: Atoms) -> None:
            if self.busy:
                self._set_error_state(
                    "Cannot replace atoms while a request is in progress.",
                    append_message=False,
                    clear_busy=False,
                    status="Busy",
                )
                return
            with self._client_lock:
                self._client.set_atoms(atoms)
                current_atoms = self._client.get_atoms()
            self._sync_xyz(current_atoms)
            self._clear_selection_state()
            self.error_text = ""
            self.status_text = "Ready"

        def get_atoms(self) -> Atoms:
            with self._client_lock:
                return self._client.get_atoms()

        def get_selected_atom_indices(self) -> list[int]:
            return list(self._selected_atom_indices)

        def clear_selection(self) -> list[int]:
            self._clear_selection_state()
            self.error_text = ""
            self.status_text = "Ready"
            return self.get_selected_atom_indices()

        def undo(self, *, raise_errors: bool = False) -> Atoms:
            if self.busy:
                message = self._set_error_state(
                    "Another request is already in progress.",
                    append_message=False,
                    clear_busy=False,
                    status="Busy",
                )
                if raise_errors:
                    raise RuntimeError(message)
                return self.get_atoms()

            try:
                with self._client_lock:
                    atoms = self._client.undo()
            except Exception as exc:
                self._set_error_state(exc)
                if raise_errors:
                    raise
                return self.get_atoms()

            self._append_message("system", "Reverted to the previous committed structure.")
            self._sync_xyz(atoms)
            self._clear_selection_state()
            self.error_text = ""
            self.status_text = "Ready"
            return self.get_atoms()

        def close(self) -> None:
            self._closed = True
            with self._client_lock:
                self._client.close()
