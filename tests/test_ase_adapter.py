from ase import Atoms

from chemflow_client.ase_adapter import AseAtomsAdapter


def test_ase_adapter_round_trip_preserves_core_fields():
    atoms = Atoms(
        symbols=["C", "O"],
        positions=[[0.0, 0.0, 0.0], [1.2, 0.0, 0.0]],
        cell=[[4.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 6.0]],
        pbc=[True, False, False],
    )
    atoms.set_tags([1, 2])
    atoms.set_masses([12.0, 16.0])

    payload = AseAtomsAdapter.to_payload(atoms)
    restored = AseAtomsAdapter.from_payload(payload)

    assert restored.get_chemical_symbols() == ["C", "O"]
    assert restored.get_positions().tolist() == [[0.0, 0.0, 0.0], [1.2, 0.0, 0.0]]
    assert restored.get_pbc().tolist() == [True, False, False]
    assert restored.get_tags().tolist() == [1, 2]
    assert restored.get_masses().tolist() == [12.0, 16.0]
