import gzip
import logging
import random
import threading
import time
import zlib
from dataclasses import dataclass
from io import BytesIO
from typing import Final, Literal, Mapping

from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http._common import _is_retryable
from opentelemetry.exporter.otlp.proto.http._transport import (
    BaseHTTPResult,
    BaseHTTPTransport,
)

_logger = logging.getLogger(__name__)

_MAX_RETRIES: Final[int] = 6


@dataclass(slots=True, frozen=True)
class ExportResult:
    success: bool
    status_code: int | None
    reason: str | None
    error: Exception | None


class OTLPHTTPClient:
    def __init__(
        self,
        transport: BaseHTTPTransport,
        endpoint: str,
        timeout: float,
        compression: Compression,
        shutdown_event: threading.Event,
        headers: Mapping[str, str],
        kind: Literal["span", "logs", "metrics"],
    ) -> None:
        self._transport = transport
        self._endpoint = endpoint
        self._timeout = timeout
        self._compression = compression
        self._shutdown_event = shutdown_event
        self._headers = dict(headers)
        self._kind = kind

    def _compress(self, serialized_data: bytes) -> bytes:
        if self._compression is Compression.Gzip:
            buf = BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="w") as gz:
                gz.write(serialized_data)
            return buf.getvalue()
        if self._compression is Compression.Deflate:
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
            and result.is_connection_error()
            and (remaining := deadline - time.time()) > 0
        ):
            # Backends may close keep-alive connections mid-flight; one
            # retry covers the common stale-connection case before
            # falling through to the outer backoff.
            result = self._transport.request(
                "POST",
                self._endpoint,
                headers=self._headers,
                data=data,
                timeout=remaining,
            )
        return result

    def export(self, data: bytes) -> ExportResult:
        data = self._compress(data)
        deadline = time.time() + self._timeout

        for retry_num in range(_MAX_RETRIES):
            backoff_seconds = 2**retry_num * random.uniform(0.8, 1.2)
            export_error: Exception | None
            retryable: bool
            status_code: int | None = None
            reason: str | None = None

            try:
                result = self._submit(data, max(deadline - time.time(), 0.0))
            except Exception as error:
                export_error = error
                retryable = False
            else:
                if (
                    result.status_code is not None
                    and 200 <= result.status_code < 400
                ):
                    return ExportResult(
                        True, result.status_code, result.reason, None
                    )
                export_error = result.error
                retryable = (
                    _is_retryable(status_code)
                    if status_code
                    else result.is_connection_error()
                )
                status_code = result.status_code
                reason = result.reason

            if not retryable:
                _logger.error(
                    "Failed to export %s batch code: %s, reason: %s",
                    self._kind,
                    status_code,
                    reason or export_error or "unknown",
                )
                return ExportResult(False, status_code, reason, export_error)

            if (
                retry_num + 1 == _MAX_RETRIES
                or backoff_seconds > (deadline - time.time())
                or self._shutdown_event.is_set()
            ):
                _logger.error(
                    "Failed to export %s batch due to timeout, "
                    "max retries or shutdown.",
                    self._kind,
                )
                return ExportResult(False, status_code, reason, export_error)

            _logger.warning(
                "Transient error %s encountered while exporting %s batch, retrying in %.2fs.",
                reason,
                self._kind,
                backoff_seconds,
            )
            shutdown = self._shutdown_event.wait(backoff_seconds)
            if shutdown:
                _logger.warning("Shutdown in progress, aborting retry.")
                break

        return ExportResult(False, None, None, None)

    def close(self) -> None:
        self._transport.close()
