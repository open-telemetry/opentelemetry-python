# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import enum
import gzip
import logging
import random
import threading
import time
import zlib
from collections.abc import Mapping
from dataclasses import dataclass
from http import HTTPStatus
from io import BytesIO
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from opentelemetry.exporter.http.transport._base import (
        BaseHTTPResult,
        BaseHTTPTransport,
    )

_logger = logging.getLogger(__name__)

_MAX_RETRIES: Final[int] = 6
_DEFAULT_TIMEOUT: Final[float] = 10.0
_DEFAULT_JITTER: Final[float] = 0.2


_RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset(
    {
        HTTPStatus.TOO_MANY_REQUESTS.value,
        HTTPStatus.BAD_GATEWAY.value,
        HTTPStatus.SERVICE_UNAVAILABLE.value,
        HTTPStatus.GATEWAY_TIMEOUT.value,
    }
)


def _is_retryable(status_code: int | None) -> bool:
    return status_code in _RETRYABLE_STATUS_CODES


def _extract_retry_after(result: BaseHTTPResult) -> float | None:
    try:
        value = result.headers().get("retry-after")
        if value is not None:
            return float(value)
    # pylint: disable-next=broad-exception-caught
    except Exception:
        pass
    return None


class Compression(enum.Enum):
    NONE = "none"
    DEFLATE = "deflate"
    GZIP = "gzip"

    @staticmethod
    def from_str(value: str) -> Compression:
        match value.strip().lower():
            case "none":
                return Compression.NONE
            case "deflate":
                return Compression.DEFLATE
            case "gzip":
                return Compression.GZIP
            case _:
                raise ValueError(
                    f"Invalid compression type: {value!r}. "
                    "Expected one of: 'none', 'deflate', 'gzip'."
                )


@dataclass(slots=True, frozen=True)
class ExportResult:
    """Outcome of an OTLP export attempt, including retry exhaustion."""

    success: bool
    status_code: int | None
    reason: str | None
    error: Exception | None


class OTLPHTTPClient:
    """Sends serialized OTLP payloads over HTTP with retry logic.

    Compression, backoff, and connection-error recovery are handled internally.
    Callers interact through the :meth:`export` and :meth:`close` methods.
    """

    def __init__(
        self,
        transport: BaseHTTPTransport,
        endpoint: str,
        kind: Literal["spans", "logs", "metrics"],
        timeout: float = _DEFAULT_TIMEOUT,
        compression: Compression = Compression.NONE,
        headers: Mapping[str, str] | None = None,
        jitter: float = _DEFAULT_JITTER,
        logger: logging.Logger | None = None,
    ) -> None:
        self._transport = transport
        self._endpoint = endpoint
        self._timeout = timeout
        self._compression = compression
        self._headers = dict(headers) if headers is not None else {}
        if self._compression is not Compression.NONE and not any(
            key.lower() == "content-encoding" for key in self._headers
        ):
            self._headers["Content-Encoding"] = self._compression.value
        self._kind = kind
        self._jitter = min(max(jitter, 0.0), 1.0)
        self._logger = logger if logger is not None else _logger
        self._shutdown = False
        self._shutdown_event = threading.Event()

    def _compute_backoff(self, retry: int) -> float:
        return 2**retry * random.uniform(1 - self._jitter, 1 + self._jitter)

    def _compress(self, serialized_data: bytes) -> bytes:
        if self._compression is Compression.GZIP:
            buf = BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="w") as gz:
                gz.write(serialized_data)
            return buf.getvalue()
        if self._compression is Compression.DEFLATE:
            return zlib.compress(serialized_data)
        return serialized_data

    def _submit(self, data: bytes, timeout: float) -> BaseHTTPResult:
        deadline = time.time() + timeout
        result = self._transport.request(
            "POST",
            self._endpoint,
            headers=self._headers,
            data=data,
            timeout=timeout,
        )
        if (
            result.error is not None
            and self._transport.is_connection_error(result.error)
            and (remaining := deadline - time.time()) > 0
        ):
            # Immediately retry connection errors once without backoff. These
            # usually indicate a stale pooled connection that the transport will
            # reestablish on the next attempt.
            result = self._transport.request(
                "POST",
                self._endpoint,
                headers=self._headers,
                data=data,
                timeout=remaining,
            )
        return result

    def export(self, data: bytes) -> ExportResult:
        """Export a serialized payload, retrying on transient failures.

        :param data: Serialized bytes to send.
        :returns: An :class:`ExportResult` indicating success or the reason for failure.
        """
        data = self._compress(data)
        deadline = time.time() + self._timeout

        for retry in range(_MAX_RETRIES):
            backoff = self._compute_backoff(retry)
            status_code: int | None = None
            reason: str | None = None
            export_error: Exception | None
            retryable: bool

            try:
                result = self._submit(data, max(deadline - time.time(), 0.0))
            # pylint: disable-next=broad-exception-caught
            except Exception as error:
                export_error = error
                retryable = False
            else:
                status_code = result.status_code
                reason = result.reason
                if status_code is not None and 200 <= status_code < 400:
                    return ExportResult(True, status_code, reason, None)
                export_error = result.error
                retryable = (
                    _is_retryable(status_code)
                    if status_code
                    else self._transport.is_connection_error(result.error)
                )
                if (
                    retryable
                    and status_code is not None
                    and (retry_after := _extract_retry_after(result))
                    is not None
                ):
                    backoff = retry_after

            if not retryable:
                self._logger.error(
                    "Failed to export %s batch code: %s, reason: %s",
                    self._kind,
                    status_code,
                    reason or export_error or "unknown",
                )
                return ExportResult(False, status_code, reason, export_error)

            if (
                retry + 1 == _MAX_RETRIES
                or backoff > (deadline - time.time())
                or self._shutdown_event.is_set()
            ):
                self._logger.error(
                    "Failed to export %s batch due to timeout, "
                    "max retries or shutdown.",
                    self._kind,
                )
                return ExportResult(False, status_code, reason, export_error)

            self._logger.warning(
                "Transient error %s encountered while exporting %s batch, retrying in %.2fs.",
                reason or export_error,
                self._kind,
                backoff,
            )
            shutdown = self._shutdown_event.wait(backoff)
            if shutdown:
                self._logger.warning("Shutdown in progress, aborting retry.")
                break

        return ExportResult(False, None, None, None)

    def shutdown(self) -> None:
        """Shutdown the client."""
        if self._shutdown:
            self._logger.warning("OTLP client already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_event.set()
        self._transport.close()
