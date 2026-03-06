# chemflow-client

Public Python client for ChemFlow 3D chat editing.

Default public service URL: `https://chemcloud.info`
Supported Python versions: 3.9+

## Install

```bash
pip install chemflow-client
```

Notebook widget support is optional:

```bash
pip install "chemflow-client[notebook]"
```

## One-shot Usage

```python
from ase.build import molecule
from chemflow_client import chat3d

atoms = molecule("H2O")
updated_atoms, text = chat3d(
    atoms,
    "change the H-O-H angle to 110 degrees",
    api_key="cfsk_xxx",
)
```

Override `base_url` only when targeting a self-hosted ChemFlow deployment.

## Stateful Usage

```python
from ase.build import molecule
from chemflow_client import ChemFlow3DClient

client = ChemFlow3DClient(
    api_key="cfsk_xxx",
)
client.start(molecule("NH3"))

atoms, text = client.chat("rotate one hydrogen slightly outward")
atoms = client.undo()
client.close()
```

## Notebook Widget

```python
from IPython.display import display
from ase.build import molecule
from chemflow_client import Chat3DWidget

widget = Chat3DWidget(
    molecule("CH4"),
    api_key="cfsk_xxx",
)
display(widget)

latest_atoms = widget.get_atoms()
selected_atoms = widget.get_selected_atom_indices()

# Start a background request and keep using the notebook.
widget.chat_async("rotate one hydrogen slightly outward")
```

The widget is a cell output widget, not a full JupyterLab sidebar extension.
Clicking atoms in the widget toggles selection with a light-yellow highlight similar to the web viewer.
During `Send`, the widget now submits in the background, shows an explicit waiting state, and disables interactive controls until the response returns.
`widget.chat_async(...)` schedules the same background workflow from Python code and returns immediately.
Notebook-triggered request failures are surfaced in the widget status/message area instead of raising by default. Pass `raise_errors=True` to `widget.chat(...)` or `widget.undo(...)` if you need Python exceptions.
