# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BaseHTTPResult(ABC):
    """Outcome of a single HTTP request made by a :class:`BaseHTTPTransport`.

    Either ``status_code`` and ``reason`` are populated (server responded),
    or ``error`` is set (request failed before a response was received).
    """

    status_code: int | None = None
    reason: str | None = None
    error: Exception | None = None

    @abstractmethod
    def is_connection_error(self) -> bool:
        """Return ``True`` if the failure is a transport-level connection error."""


class BaseHTTPTransport(ABC):
    """Abstract HTTP transport interface used by OTLP HTTP exporters."""

    @abstractmethod
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        data: bytes | None = None,
    ) -> BaseHTTPResult:
        """Send an HTTP request and return the result.

        :param method: HTTP method (e.g. ``"POST"``).
        :param url: Target URL.
        :param headers: Optional HTTP headers to include in the request.
        :param timeout: Optional request timeout in seconds.
        :param data: Optional request body.
        :returns: A :class:`BaseHTTPResult` describing the outcome.
        """

    @abstractmethod
    def close(self) -> None:
        """Release any resources held by the transport."""
