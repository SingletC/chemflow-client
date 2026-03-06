"""ASE conversion helpers for the public ChemFlow client."""

from __future__ import annotations

from ase import Atoms

from .types import AtomsPayload


class AseAtomsAdapter:
    """Convert between `ase.Atoms` and ChemFlow SDK payloads."""

    @staticmethod
    def copy_atoms(atoms: Atoms) -> Atoms:
        return atoms.copy()

    @staticmethod
    def to_payload(atoms: Atoms) -> AtomsPayload:
        if len(atoms) == 0:
            return AtomsPayload(symbols=[], positions=[])
        tags = None
        masses = None
        try:
            tags = atoms.get_tags().tolist()
        except Exception:
            tags = None
        try:
            masses = atoms.get_masses().tolist()
        except Exception:
            masses = None
        cell = atoms.get_cell().array.tolist() if atoms.get_cell() is not None else None
        pbc = atoms.get_pbc().tolist() if atoms.get_pbc() is not None else None
        return AtomsPayload(
            symbols=atoms.get_chemical_symbols(),
            positions=atoms.get_positions().tolist(),
            cell=cell,
            pbc=pbc,
            tags=tags,
            masses=masses,
        )

    @staticmethod
    def from_payload(payload: AtomsPayload) -> Atoms:
        atoms = Atoms(
            symbols=list(payload.symbols),
            positions=[list(row) for row in list(payload.positions)],
            cell=[list(row) for row in list(payload.cell)] if payload.cell is not None else None,
            pbc=list(payload.pbc) if payload.pbc is not None else None,
        )
        if payload.tags is not None:
            atoms.set_tags(list(payload.tags))
        if payload.masses is not None:
            atoms.set_masses(list(payload.masses))
        return atoms

    @staticmethod
    def to_xyz_text(atoms: Atoms) -> str:
        if len(atoms) == 0:
            return ""
        lines = [str(len(atoms)), "ChemFlow Client"]
        for symbol, position in zip(atoms.get_chemical_symbols(), atoms.get_positions()):
            lines.append(
                f"{symbol} {position[0]:.16g} {position[1]:.16g} {position[2]:.16g}"
            )
        return "\n".join(lines)
