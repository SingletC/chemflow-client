"""Typed payloads for the ChemFlow SDK API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


def _copy_matrix(value: Optional[list[list[float]]]) -> Optional[list[list[float]]]:
    if value is None:
        return None
    return [list(row) for row in list(value)]


@dataclass(frozen=True)
class AtomsPayload:
    """Serialized ASE atoms payload used by the SDK endpoint."""

    symbols: list[str]
    positions: list[list[float]]
    cell: Optional[list[list[float]]] = None
    pbc: Optional[list[bool]] = None
    tags: Optional[list[int]] = None
    masses: Optional[list[float]] = None

    def to_request_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "symbols": list(self.symbols),
            "positions": _copy_matrix(self.positions) or [],
        }
        if self.cell is not None:
            payload["cell"] = _copy_matrix(self.cell)
        if self.pbc is not None:
            payload["pbc"] = list(self.pbc)
        if self.tags is not None:
            payload["tags"] = list(self.tags)
        if self.masses is not None:
            payload["masses"] = list(self.masses)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AtomsPayload":
        return cls(
            symbols=[str(item) for item in list(data.get("symbols") or [])],
            positions=_copy_matrix(data.get("positions") or []) or [],
            cell=_copy_matrix(data.get("cell")),
            pbc=list(data.get("pbc") or []) or None,
            tags=list(data.get("tags") or []) or None,
            masses=[float(item) for item in list(data.get("masses") or [])] or None,
        )


@dataclass(frozen=True)
class Chat3DRequest:
    """Request payload for `/api/sdk/chat3d`."""

    prompt: str
    session_id: Optional[str] = None
    atoms: Optional[AtomsPayload] = None
    model: Optional[str] = None

    def to_request_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"prompt": self.prompt}
        if self.session_id is not None:
            payload["session_id"] = self.session_id
        if self.atoms is not None:
            payload["atoms"] = self.atoms.to_request_dict()
        if self.model is not None:
            payload["model"] = self.model
        return payload


@dataclass(frozen=True)
class Chat3DResponse:
    """Response payload for `/api/sdk/chat3d`."""

    session_id: Optional[str]
    assistant_message: str
    atoms: Optional[AtomsPayload]
    changed: bool
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chat3DResponse":
        atoms_data = data.get("atoms")
        return cls(
            session_id=data.get("session_id"),
            assistant_message=str(data.get("assistant_message") or ""),
            atoms=AtomsPayload.from_dict(atoms_data) if isinstance(atoms_data, dict) else None,
            changed=bool(data.get("changed", False)),
            error=data.get("error"),
        )
