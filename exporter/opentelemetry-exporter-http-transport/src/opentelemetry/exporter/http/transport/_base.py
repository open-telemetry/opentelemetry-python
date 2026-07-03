# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any


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
    def content(self) -> bytes:
        """Return the raw response body.

        Implementations may raise an exception if the returned content is malformed.
        """

    @abstractmethod
    def headers(self) -> Mapping[str, str]:
        """Return the response headers.

        The returned mapping MUST be case-insensitive with respect to header
        keys. Headers with multiple values are represented as a single string
        of comma separated values.

        Implementations may raise an exception the returned headers are malformed.
        """

    def text(self) -> str:
        """Return the response body decoded as UTF-8.

        Implementations may raise an exception if the returned string is malformed.
        """
        return self.content().decode("utf-8")

    def json(self) -> Any:
        """Return the response body parsed as JSON.

        Implementations may raise an exception if no response content
        is available or the returned JSON is malformed.
        """
        return json.loads(self.text())


class BaseHTTPTransport(ABC):
    """Abstract HTTP transport interface used by HTTP exporters."""

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

    @abstractmethod
    def is_connection_error(self, exception: Exception | None) -> bool:
        """Return ``True`` if the exception is a transport-level connection error."""
