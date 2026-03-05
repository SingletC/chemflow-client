from ase import Atoms

from chemflow_client.client import ChemFlow3DClient, chat3d
from chemflow_client.exceptions import ChemFlowStateError
from chemflow_client.types import AtomsPayload, Chat3DResponse


def test_chat3d_one_shot(monkeypatch):
    def fake_chat3d(self, request):
        payload = request.atoms
        assert payload is not None
        positions = [list(row) for row in payload.positions]
        positions[0][0] += 1.0
        return Chat3DResponse(
            session_id="session-1",
            assistant_message="Applied edit.",
            atoms=AtomsPayload(
                symbols=list(payload.symbols),
                positions=positions,
                cell=payload.cell,
                pbc=payload.pbc,
                tags=payload.tags,
                masses=payload.masses,
            ),
            changed=True,
        )

    monkeypatch.setattr("chemflow_client.api.ChemFlowApi.chat3d", fake_chat3d)

    atoms = Atoms(symbols=["H", "H"], positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 0.74]])
    updated_atoms, text = chat3d(
        atoms,
        "stretch the bond",
        base_url="http://localhost:8000",
        api_key="cfsk_test_key",
    )

    assert abs(updated_atoms.get_positions()[0][0] - 1.0) < 1e-8
    assert text == "Applied edit."


def test_stateful_client_set_atoms_and_undo(monkeypatch):
    calls = []

    def fake_chat3d(self, request):
        calls.append(request)
        source = request.atoms
        if source is None:
            raise AssertionError("Expected explicit atoms payload for this test path.")
        positions = [list(row) for row in source.positions]
        positions[0][0] += 2.0
        return Chat3DResponse(
            session_id="session-2",
            assistant_message="Shifted.",
            atoms=AtomsPayload(
                symbols=list(source.symbols),
                positions=positions,
                cell=source.cell,
                pbc=source.pbc,
                tags=source.tags,
                masses=source.masses,
            ),
            changed=True,
        )

    monkeypatch.setattr("chemflow_client.api.ChemFlowApi.chat3d", fake_chat3d)

    client = ChemFlow3DClient(base_url="http://localhost:8000", api_key="cfsk_test_key")
    client.start(Atoms(symbols=["He"], positions=[[0.0, 0.0, 0.0]]))

    first_atoms, _ = client.chat("move it")
    assert abs(first_atoms.get_positions()[0][0] - 2.0) < 1e-8
    assert calls[0].session_id is None
    assert calls[0].atoms is not None

    client.set_atoms(Atoms(symbols=["He"], positions=[[5.0, 0.0, 0.0]]))
    second_atoms, _ = client.chat("move it again")
    assert abs(second_atoms.get_positions()[0][0] - 7.0) < 1e-8
    assert calls[1].session_id == "session-2"
    assert calls[1].atoms is not None

    undone = client.undo()
    assert abs(undone.get_positions()[0][0] - 5.0) < 1e-8
    assert client.session_id is None
    client.close()


def test_undo_requires_previous_committed_structure():
    client = ChemFlow3DClient(base_url="http://localhost:8000", api_key="cfsk_test_key")
    client.start(Atoms(symbols=["Ne"], positions=[[0.0, 0.0, 0.0]]))
    try:
        client.undo()
        assert False, "Expected ChemFlowStateError"
    except ChemFlowStateError:
        pass
    finally:
        client.close()
