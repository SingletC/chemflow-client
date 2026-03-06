"""High-level stateful ChemFlow 3D client."""

from __future__ import annotations

from typing import Optional, Tuple

from ase import Atoms

from .api import ChemFlowApi
from .ase_adapter import AseAtomsAdapter
from .exceptions import ChemFlowResponseError, ChemFlowStateError
from .types import Chat3DRequest


class ChemFlow3DClient:
    """Stateful ChemFlow 3D client with client-side one-step undo."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0,
    ) -> None:
        self._api = ChemFlowApi(base_url=base_url, api_key=api_key, timeout=timeout)
        self._model = model
        self._atoms: Optional[Atoms] = None
        self._previous_atoms: Optional[Atoms] = None
        self._session_id: Optional[str] = None
        self._needs_sync = False

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    def start(self, atoms: Optional[Atoms] = None) -> None:
        """Start a session from an existing structure or an empty workspace."""
        self._atoms = AseAtomsAdapter.copy_atoms(atoms) if atoms is not None else Atoms()
        self._previous_atoms = None
        self._session_id = None
        self._needs_sync = False

    def get_atoms(self) -> Atoms:
        if self._atoms is None:
            raise ChemFlowStateError("No structure has been loaded. Call start(atoms) first.")
        return AseAtomsAdapter.copy_atoms(self._atoms)

    def set_atoms(self, atoms: Atoms) -> None:
        self._atoms = AseAtomsAdapter.copy_atoms(atoms)
        self._needs_sync = True

    def chat(self, prompt: str) -> Tuple[Atoms, str]:
        if self._atoms is None:
            raise ChemFlowStateError("No structure has been loaded. Call start(atoms) first.")
        normalized_prompt = (prompt or "").strip()
        if not normalized_prompt:
            raise ValueError("prompt is required")

        outgoing_atoms = None
        if self._session_id is None or self._needs_sync:
            outgoing_atoms = AseAtomsAdapter.to_payload(self._atoms)

        previous_atoms = AseAtomsAdapter.copy_atoms(self._atoms)
        response = self._api.chat3d(
            Chat3DRequest(
                prompt=normalized_prompt,
                session_id=self._session_id,
                atoms=outgoing_atoms,
                model=self._model,
            )
        )
        if response.error:
            raise ChemFlowResponseError(response.error, response=response)
        if response.atoms is None:
            raise ChemFlowResponseError("ChemFlow response did not include atoms.", response=response)

        self._previous_atoms = previous_atoms
        self._atoms = AseAtomsAdapter.from_payload(response.atoms)
        self._session_id = response.session_id
        self._needs_sync = False
        return self.get_atoms(), response.assistant_message

    def undo(self) -> Atoms:
        if self._previous_atoms is None:
            raise ChemFlowStateError("No previous committed structure is available for undo.")
        self._atoms = AseAtomsAdapter.copy_atoms(self._previous_atoms)
        self._previous_atoms = None
        self._session_id = None
        self._needs_sync = False
        return self.get_atoms()

    def close(self) -> None:
        self._api.close()
        self._session_id = None
        self._needs_sync = False

    def __enter__(self) -> "ChemFlow3DClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def chat3d(
    atoms: Optional[Atoms],
    prompt: str,
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: float = 300.0,
) -> Tuple[Atoms, str]:
    """Run a one-shot 3D chat edit from existing atoms or an empty workspace."""
    with ChemFlow3DClient(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout=timeout,
    ) as client:
        client.start(atoms)
        return client.chat(prompt)
