# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import typing as _t

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    httpx = None  # type: ignore

import requests


class _ResponseAdapter:
    def __init__(self, resp: "httpx.Response") -> None:  # type: ignore[name-defined]
        self._resp = resp
        self.ok: bool = resp.is_success
        self.status_code: int = resp.status_code
        # reason_phrase is available on httpx.Response
        self.reason: str = getattr(resp, "reason_phrase", "")
        self.headers: _t.Mapping[str, str] = resp.headers


class HttpxSession:
    """Minimal requests-compatible session backed by httpx.Client.

    - Exposes a dict-like ``headers`` attribute for parity with requests.Session.
    - Provides ``post`` and ``close`` methods used by OTLP HTTP exporters.
    - Negotiates HTTP/2 when available, falls back to HTTP/1.1 on negotiation errors.
    """

    def __init__(self) -> None:
        if httpx is None:  # pragma: no cover - guarded by importorskip in tests
            raise RuntimeError("httpx is not available")
        self.headers: dict[str, str] = {}
        self._client: "httpx.Client | None" = None  # type: ignore[name-defined]
        self._http2_enabled: bool = True

    def _ensure_client(self, verify: _t.Any, cert: _t.Any, timeout: float) -> None:
        if self._client is None:
            # Create client lazily to honor any header updates performed before the first request
            self._client = httpx.Client(  # type: ignore[attr-defined]
                http2=self._http2_enabled,
                headers=self.headers.copy(),
                verify=verify,
                cert=cert,
                timeout=timeout,
            )

    def post(
        self,
        url: str,
        data: bytes,
        verify: _t.Any,
        timeout: float,
        cert: _t.Any,
    ) -> _ResponseAdapter:
        self._ensure_client(verify, cert, timeout)
        try:
            resp = self._client.post(url, content=data)  # type: ignore[union-attr]
            return _ResponseAdapter(resp)
        except Exception as exc:  # httpx.HTTPError and transport errors
            # Fallback to HTTP/1.1 on first HTTP/2 failure, then re-raise as requests exception
            if self._http2_enabled:
                self._http2_enabled = False
                try:
                    if self._client is not None:
                        self._client.close()
                    self._client = None
                    self._ensure_client(verify, cert, timeout)
                    resp = self._client.post(url, content=data)  # type: ignore[union-attr]
                    return _ResponseAdapter(resp)
                except Exception as exc2:
                    raise requests.exceptions.RequestException(str(exc2)) from exc2
            raise requests.exceptions.RequestException(str(exc)) from exc

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None
