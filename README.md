# chemflow-client

Public Python client for ChemFlow 3D chat editing.

Supported Python versions: 3.9+

## Install

```bash
pip install chemflow-client
```

Notebook widget support is optional:

```bash
pip install "chemflow-client[notebook]"
```

For contributors who want to run the full test suite:

```bash
pip install -e ".[dev,notebook]"
```

## Usage

Blocking Python API:

```python
from ase.build import molecule
from chemflow_client import chat3d

atoms = molecule("H2O")
updated_atoms, text = chat3d(
    prompt="change the H-O-H angle to 110 degrees",
    atoms=atoms,
)
# or generate one directly.
generated_atoms, text = chat3d(prompt="generate methane")
```

## JupyterLab

Async notebook widget:

```python
from chemflow_client import Chat3DWidget

widget = Chat3DWidget()
widget
```

```python
widget.get_atoms()
```

![JupyterLab widget demo](https://raw.githubusercontent.com/SingletC/chemflow-client/v0.1.5/docs/assets/chemflow-widget-demo.gif)


## Configure

Create an API key at <https://chemflow.cloud/user-center/api-keys>.

You can configure the client with environment variables:

```bash
export CHEMFLOW_API_KEY="cfsk_xxx"
```

You can also pass configuration as arguments to `chat3d(...)` or `Chat3DWidget(...)`:

```python
from chemflow_client import Chat3DWidget, chat3d

updated_atoms, text = chat3d(
    prompt="generate methane",
    api_key="cfsk_xxx",
)

widget = Chat3DWidget(api_key="cfsk_xxx")
```

## Call Signatures

### `chat3d(...)`

```python
chat3d(
    *,
    prompt: str,
    atoms: Optional[Atoms] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: float = 300.0,
) -> Tuple[Atoms, str]
```

- `prompt`: Required keyword-only editing or generation instruction.
- `atoms`: Optional initial `ase.Atoms` structure.
- `base_url`, `api_key`, `model`, `timeout`: Optional client configuration overrides.
- Returns `(atoms, text)`.

### `Chat3DWidget(...)`

```python
Chat3DWidget(
    atoms: Optional[Atoms] = None,
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: float = 300.0,
)
```

- `atoms`: Optional initial `ase.Atoms` structure.
- `base_url`, `api_key`, `model`, `timeout`: Optional client configuration overrides.
- Returns a notebook widget instance backed by `ChemFlow3DClient`.
