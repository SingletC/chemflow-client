from chemflow_client.widget import (
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
