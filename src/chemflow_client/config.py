"""Configuration helpers for chemflow-client."""

from __future__ import annotations

import os
from typing import Optional

from .constants import (
    CHEMFLOW_API_KEY_ENV_VAR,
    CHEMFLOW_BASE_URL_ENV_VAR,
    DEFAULT_BASE_URL,
)
from .exceptions import ChemFlowConfigurationError


def resolve_base_url(base_url: Optional[str]) -> str:
    normalized = (base_url or os.getenv(CHEMFLOW_BASE_URL_ENV_VAR) or DEFAULT_BASE_URL).strip()
    normalized = normalized.rstrip("/")
    if not normalized:
        raise ChemFlowConfigurationError("base_url is required")
    return normalized


def resolve_api_key(api_key: Optional[str]) -> str:
    normalized = (api_key or os.getenv(CHEMFLOW_API_KEY_ENV_VAR) or "").strip()
    if not normalized:
        raise ChemFlowConfigurationError(
            "api_key is required. Pass api_key=... or set CHEMFLOW_API_KEY."
        )
    return normalized
