"""Client exceptions."""

from __future__ import annotations

from typing import Any


class ChemFlowError(Exception):
    """Base class for all ChemFlow client errors."""


class ChemFlowConfigurationError(ChemFlowError):
    """Raised when client configuration is invalid."""


class ChemFlowStateError(ChemFlowError):
    """Raised when stateful client methods are used incorrectly."""


class ChemFlowHttpError(ChemFlowError):
    """Raised when the backend returns an HTTP error."""

    def __init__(self, status_code: int, message: str, *, body: Any = None) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = int(status_code)
        self.message = message
        self.body = body


class ChemFlowResponseError(ChemFlowError):
    """Raised when the backend returns a structured error payload."""

    def __init__(self, message: str, *, response: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.response = response
