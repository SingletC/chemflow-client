# chemflow-client

Public Python client for ChemFlow 3D chat editing.

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
    base_url="http://localhost:8000",
    api_key="cfsk_xxx",
)
```

## Stateful Usage

```python
from ase.build import molecule
from chemflow_client import ChemFlow3DClient

client = ChemFlow3DClient(
    base_url="http://localhost:8000",
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
    base_url="http://localhost:8000",
    api_key="cfsk_xxx",
)
display(widget)

latest_atoms = widget.get_atoms()
```

The widget is a cell output widget, not a full JupyterLab sidebar extension.
