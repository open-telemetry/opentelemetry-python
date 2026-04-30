# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import gzip
import logging
import random
import threading
import zlib
from dataclasses import dataclass
from io import BytesIO
from time import time
from typing import Generic, TypeVar, Final, Any, Literal, Mapping

from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http._common import _is_retryable
from opentelemetry.exporter.otlp.proto.http._session import (
    HttpSession, HttpResponse,
)

_logger = logging.getLogger(__name__)

_MAX_RETRIES: Final[int] = 6
_CONNECTION_ERRORS: Final[frozenset[str]] = frozenset({
    "urllib3.exceptions.ProtocolError",
    "urllib3.exceptions.ProxyError",
    "urllib3.exceptions.TimeoutError",
    "urllib3.exceptions.ReadTimeoutError",
    "urllib3.exceptions.ConnectTimeoutError",
    "urllib3.exceptions.NewConnectionError",
    "requests.exceptions.ConnectionError",
    "requests.exceptions.ProxyError",
    "requests.exceptions.ConnectTimeout",
    "requests.exceptions.ReadTimeout",
})

T = TypeVar("T", bound=HttpSession)


@dataclass(slots=True, frozen=True)
class ExportResult:
    success: bool
    status_code: int | None
    error: Exception | None


class OTLPHttpClient(Generic[T]):
    """Shared HTTP transport used by the OTLP HTTP exporters.

    Owns compression, the POST request, and the retry loop with
    exponential backoff bounded by an absolute deadline. Generic over
    the :class:`HttpSession` implementation.
    """

    def __init__(
        self,
        session: T,
        endpoint: str,
        timeout: float,
        compression: Compression,
        shutdown_event: threading.Event,
        headers: Mapping[str, str],
        kind: Literal["span", "logs", "metrics"],
    ) -> None:
        self._session: T = session
        self._endpoint = endpoint
        self._timeout = timeout
        self._compression = compression
        self._shutdown_event = shutdown_event
        self._headers = headers
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

    def _submit(self, data: bytes, timeout: float) -> HttpResponse:
        try:
            return self._session.request(
                "POST",
                self._endpoint,
                headers=dict(self._headers),
                data=data,
                timeout=timeout,
            )
        except Exception as error:
            if _get_fqn(type(error)) not in _CONNECTION_ERRORS:
                raise
            # Backends may close keep-alive connections mid-flight; one
            # retry covers the common stale-connection case before
            # falling through to the outer backoff.
            return self._session.request(
                "POST",
                self._endpoint,
                headers=dict(self._headers),
                data=data,
                timeout=timeout,
            )

    def export(self, data: bytes) -> ExportResult:
        data = self._compress(data)
        deadline_sec = time() + self._timeout

        for retry_num in range(_MAX_RETRIES):
            backoff_seconds = 2**retry_num * random.uniform(0.8, 1.2)
            export_error: Exception | None = None
            status_code: int | None = None
            retryable: bool
            reason: str | Exception | None

            try:
                resp = self._submit(data, max(deadline_sec - time(), 0.0))
            except Exception as error:
                export_error = error
                reason = error
                retryable = _get_fqn(type(error)) in _CONNECTION_ERRORS
            else:
                status_code = resp.status_code
                if 200 <= status_code < 400:
                    return ExportResult(True, status_code, None)
                reason = resp.reason
                retryable = _is_retryable(resp)

            if not retryable:
                _logger.error(
                    "Failed to export %s batch code: %s, reason: %s",
                    self._kind,
                    status_code,
                    reason,
                )
                return ExportResult(False, status_code, export_error)

            if (
                retry_num + 1 == _MAX_RETRIES
                or backoff_seconds > (deadline_sec - time())
                or self._shutdown_event.is_set()
            ):
                _logger.error(
                    "Failed to export %s batch due to timeout, "
                    "max retries or shutdown.",
                    self._kind,
                )
                return ExportResult(False, status_code, export_error)

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

        return ExportResult(False, None, None)

    def close(self) -> None:
        self._session.close()


def _get_fqn(ty: type) -> str:
    module = ty.__module__
    if module is None or module == 'builtins':
        return ty.__qualname__
    return f"{module}.{ty.__qualname__}"
