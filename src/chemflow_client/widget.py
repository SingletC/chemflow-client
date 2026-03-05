"""Notebook widget for ChemFlow 3D chat."""

from __future__ import annotations

import json

from ase import Atoms

from .ase_adapter import AseAtomsAdapter
from .client import ChemFlow3DClient

try:
    import anywidget
    import traitlets
except ImportError:  # pragma: no cover - optional dependency path
    anywidget = None
    traitlets = None


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

function buildMessageHtml(messages) {
  return messages.map((entry) => {
    const role = entry.role || "assistant";
    const text = entry.text || "";
    return `<div class="cf-msg cf-msg-${role}"><div class="cf-role">${role}</div><div class="cf-text">${text}</div></div>`;
  }).join("");
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
        .cf-messages { flex: 1; overflow: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
        .cf-msg { padding: 10px 12px; border-radius: 12px; border: 1px solid #d7c6ab; background: rgba(255,255,255,0.8); }
        .cf-msg-user { background: #dfe9f3; border-color: #b8cadb; }
        .cf-msg-system { background: #efe6d6; border-color: #d8c8ad; }
        .cf-role { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; margin-bottom: 4px; }
        .cf-text { white-space: pre-wrap; line-height: 1.4; }
        .cf-form { display: flex; gap: 10px; padding: 14px; border-top: 1px solid #d8ccb7; background: rgba(255,255,255,0.62); }
        .cf-input { flex: 1; border: 1px solid #b8aa91; border-radius: 10px; padding: 10px 12px; background: #fffdf8; }
        .cf-button { border: 0; border-radius: 10px; padding: 10px 14px; cursor: pointer; background: #1d5c63; color: white; }
        .cf-button-secondary { background: #8c6b3f; }
        @media (max-width: 860px) {
          .cf-grid { grid-template-columns: 1fr; }
          .cf-side { border-left: 0; border-top: 1px solid #d8ccb7; }
        }
      </style>
      <div class="cf-grid">
        <div class="cf-viewer"></div>
        <div class="cf-side">
          <div class="cf-status"></div>
          <div class="cf-messages"></div>
          <form class="cf-form">
            <input class="cf-input" type="text" placeholder="Describe the structural edit" />
            <button class="cf-button" type="submit">Send</button>
            <button class="cf-button cf-button-secondary" type="button">Undo</button>
          </form>
        </div>
      </div>
    </div>
  `;

  const viewerEl = el.querySelector(".cf-viewer");
  const statusEl = el.querySelector(".cf-status");
  const messagesEl = el.querySelector(".cf-messages");
  const formEl = el.querySelector(".cf-form");
  const inputEl = el.querySelector(".cf-input");
  const undoButton = el.querySelector(".cf-button-secondary");
  let viewer = null;
  let disposed = false;

  async function renderViewer() {
    const xyzText = model.get("xyz_text") || "";
    const $3Dmol = await ensure3Dmol();
    if (disposed) {
      return;
    }
    if (!viewer) {
      viewer = $3Dmol.createViewer(viewerEl, { backgroundColor: "#f7f2e8" });
    }
    viewer.clear();
    if (xyzText.trim()) {
      viewer.addModel(xyzText, "xyz");
      viewer.setStyle({}, { stick: { radius: 0.16 }, sphere: { scale: 0.28 } });
      viewer.zoomTo();
    }
    viewer.render();
  }

  function renderMessages() {
    const messages = parseMessages(model.get("messages_json"));
    messagesEl.innerHTML = buildMessageHtml(messages);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function renderStatus() {
    const errorText = model.get("error_text") || "";
    const statusText = model.get("status_text") || "Ready";
    statusEl.dataset.error = errorText ? "true" : "false";
    statusEl.textContent = errorText || statusText;
  }

  formEl.addEventListener("submit", (event) => {
    event.preventDefault();
    const prompt = (inputEl.value || "").trim();
    if (!prompt) {
      return;
    }
    inputEl.value = "";
    model.send({ type: "chat", prompt });
  });

  undoButton.addEventListener("click", () => {
    model.send({ type: "undo" });
  });

  model.on("change:xyz_text", renderViewer);
  model.on("change:messages_json", renderMessages);
  model.on("change:status_text", renderStatus);
  model.on("change:error_text", renderStatus);

  renderViewer();
  renderMessages();
  renderStatus();

  return () => {
    disposed = true;
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

        def __init__(
            self,
            atoms: Atoms,
            *,
            base_url: str,
            api_key: str,
            model: str | None = None,
            timeout: float = 300.0,
        ) -> None:
            super().__init__()
            self._client = ChemFlow3DClient(
                base_url=base_url,
                api_key=api_key,
                model=model,
                timeout=timeout,
            )
            self._client.start(atoms)
            self._messages: list[dict[str, str]] = []
            self._sync_xyz(self._client.get_atoms())
            self.on_msg(self._handle_frontend_message)

        def _sync_xyz(self, atoms: Atoms) -> None:
            self.xyz_text = AseAtomsAdapter.to_xyz_text(atoms)

        def _sync_messages(self) -> None:
            self.messages_json = json.dumps(self._messages)

        def _append_message(self, role: str, text: str) -> None:
            normalized_text = (text or "").strip()
            if not normalized_text:
                return
            self._messages.append({"role": role, "text": normalized_text})
            self._sync_messages()

        def _handle_frontend_message(self, _, content, buffers) -> None:
            message_type = (content or {}).get("type")
            try:
                if message_type == "chat":
                    self.chat(str((content or {}).get("prompt") or ""))
                    return
                if message_type == "undo":
                    self.undo()
                    return
            except Exception as exc:
                self.status_text = "Error"
                self.error_text = str(exc)

        def chat(self, prompt: str) -> tuple[Atoms, str]:
            normalized_prompt = (prompt or "").strip()
            if not normalized_prompt:
                raise ValueError("prompt is required")
            self.error_text = ""
            self.status_text = "Running..."
            self._append_message("user", normalized_prompt)
            atoms, text = self._client.chat(normalized_prompt)
            self._append_message("assistant", text)
            self._sync_xyz(atoms)
            self.status_text = "Ready"
            return self.get_atoms(), text

        def set_atoms(self, atoms: Atoms) -> None:
            self._client.set_atoms(atoms)
            self._sync_xyz(self._client.get_atoms())
            self.error_text = ""
            self.status_text = "Ready"

        def get_atoms(self) -> Atoms:
            return self._client.get_atoms()

        def undo(self) -> Atoms:
            atoms = self._client.undo()
            self._append_message("system", "Reverted to the previous committed structure.")
            self._sync_xyz(atoms)
            self.error_text = ""
            self.status_text = "Ready"
            return self.get_atoms()

        def close(self) -> None:
            self._client.close()
