"""Low-level HTTP client for the public ChemFlow SDK."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from .constants import DEFAULT_BASE_URL
from .exceptions import ChemFlowConfigurationError, ChemFlowHttpError
from .types import Chat3DRequest, Chat3DResponse


class ChemFlowApi:
    """Thin synchronous API wrapper around the ChemFlow SDK endpoints."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str,
        timeout: float = 300.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        normalized_base_url = (base_url or "").strip().rstrip("/")
        if not normalized_base_url:
            raise ChemFlowConfigurationError("base_url is required")
        if not api_key:
            raise ChemFlowConfigurationError("api_key is required")
        self._client = httpx.Client(
            base_url=normalized_base_url,
            timeout=timeout,
            transport=transport,
            headers={
                "X-ChemFlow-Api-Key": api_key,
                "User-Agent": "chemflow-client/0.1.0",
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        self._client.close()

    def chat3d(self, request: Chat3DRequest) -> Chat3DResponse:
        response = self._client.post("/api/sdk/chat3d", json=request.to_request_dict())
        if response.status_code >= 400:
            raise ChemFlowHttpError(
                response.status_code,
                self._extract_error_message(response),
                body=self._safe_json(response),
            )
        return Chat3DResponse.from_dict(self._safe_json(response))

    def _extract_error_message(self, response: httpx.Response) -> str:
        payload = self._safe_json(response)
        if isinstance(payload, dict):
            detail = payload.get("detail")
            error = payload.get("error")
            if isinstance(detail, str) and detail.strip():
                return detail.strip()
            if isinstance(error, str) and error.strip():
                return error.strip()
        text = (response.text or "").strip()
        return text or "Request failed"

    @staticmethod
    def _safe_json(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return {"error": (response.text or "").strip()}
