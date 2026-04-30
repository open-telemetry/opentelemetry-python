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
import http.client
import logging
import random
import ssl
import threading
import zlib
from io import BytesIO
from os import environ
from time import time
from typing import Any, Dict, NamedTuple, Optional
from urllib.parse import urlparse

from opentelemetry.exporter.otlp.proto.common._exporter_metrics import (
    ExporterMetrics,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.semconv.attributes.http_attributes import (
    HTTP_RESPONSE_STATUS_CODE,
)
from opentelemetry.util.re import parse_env_headers

from .. import Compression, _OTLP_HTTP_HEADERS, _compression_from_env

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_TIMEOUT = 10  # in seconds
_MAX_RETRYS = 6


class _OTLPHTTPResponse:
    """Minimal HTTP response wrapper exposing the fields the exporters need."""

    __slots__ = ("status_code", "reason", "ok")

    def __init__(self, status: int, reason: str) -> None:
        self.status_code = status
        self.reason = reason
        self.ok = 200 <= status < 300


class _OTLPHTTPClient:
    """Lightweight HTTP(S) client for OTLP export using only stdlib.

    Replaces requests.Session to avoid pulling in requests, urllib3,
    charset_normalizer, idna, and certifi at import time.
    """

    def __init__(
        self,
        endpoint: str,
        certificate_file,  # True (system CA) | False (no verify) | str (CA path)
        client_key_file: Optional[str],
        client_certificate_file: Optional[str],
        timeout: float,
        headers: dict,
    ) -> None:
        parsed = urlparse(endpoint)
        self._scheme = parsed.scheme
        self._host = parsed.hostname
        self._port = parsed.port
        self._path = parsed.path or "/"
        if parsed.query:
            self._path += "?" + parsed.query
        self._timeout = timeout
        self.headers: dict = dict(headers)
        self._certificate_file = certificate_file
        self._client_key_file = client_key_file
        self._client_certificate_file = client_certificate_file
        self._conn: Optional[http.client.HTTPConnection] = None

    def _ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        if self._certificate_file is False:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        elif isinstance(self._certificate_file, str):
            ctx.load_verify_locations(self._certificate_file)
        # True → ssl.create_default_context() already uses the system CA bundle
        if self._client_certificate_file and self._client_key_file:
            ctx.load_cert_chain(
                self._client_certificate_file, self._client_key_file
            )
        elif self._client_certificate_file:
            ctx.load_cert_chain(self._client_certificate_file)
        return ctx

    def _new_connection(self, timeout: float) -> http.client.HTTPConnection:
        if self._scheme == "https":
            return http.client.HTTPSConnection(
                self._host,
                self._port or 443,
                timeout=timeout,
                context=self._ssl_context(),
            )
        return http.client.HTTPConnection(
            self._host,
            self._port or 80,
            timeout=timeout,
        )

    def post(self, data: bytes, timeout: float) -> _OTLPHTTPResponse:
        headers = {**self.headers, "Content-Length": str(len(data))}
        for attempt in range(2):
            try:
                if self._conn is None:
                    self._conn = self._new_connection(timeout)
                # Update the socket timeout for this specific request so the
                # decreasing deadline passed by the retry loop is respected.
                if self._conn.sock is not None:
                    self._conn.sock.settimeout(timeout)
                self._conn.request("POST", self._path, data, headers)
                resp = self._conn.getresponse()
                resp.read()  # drain body so the connection can be reused
                return _OTLPHTTPResponse(resp.status, resp.reason)
            except (
                http.client.RemoteDisconnected,
                http.client.CannotSendRequest,
                http.client.CannotSendHeader,
                http.client.ResponseNotReady,
                ConnectionResetError,
                BrokenPipeError,
            ):
                # Stale keep-alive connection; drop it and retry once.
                self._conn = None
                if attempt == 1:
                    raise

        raise AssertionError("unreachable")  # pragma: no cover

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            self._conn = None


def _is_retryable(resp: _OTLPHTTPResponse) -> bool:
    if resp.status_code == 408:
        return True
    if 500 <= resp.status_code <= 599:
        return True
    return False


class _SignalConfig(NamedTuple):
    endpoint_env_var: str
    certificate_env_var: str
    client_key_env_var: str
    client_certificate_env_var: str
    headers_env_var: str
    timeout_env_var: str
    compression_env_var: str
    default_path: str
    metrics_component_type: Any
    metrics_signal: str


def _append_path(endpoint: str, path: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + path
    return endpoint + f"/{path}"


class _OTLPHTTPExporterBase:
    def __init__(
        self,
        endpoint: Optional[str],
        certificate_file,
        client_key_file: Optional[str],
        client_certificate_file: Optional[str],
        headers: Optional[Dict[str, str]],
        timeout: Optional[float],
        compression: Optional[Compression],
        meter_provider: Optional[MeterProvider],
        signal_config: _SignalConfig,
    ):
        self._shutdown_in_progress = threading.Event()
        self._endpoint = endpoint or environ.get(
            signal_config.endpoint_env_var,
            _append_path(
                environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, DEFAULT_ENDPOINT),
                signal_config.default_path,
            ),
        )
        self._certificate_file = certificate_file or environ.get(
            signal_config.certificate_env_var,
            environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE, True),
        )
        self._client_key_file = client_key_file or environ.get(
            signal_config.client_key_env_var,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY, None),
        )
        self._client_certificate_file = client_certificate_file or environ.get(
            signal_config.client_certificate_env_var,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE, None),
        )
        self._client_cert = (
            (self._client_certificate_file, self._client_key_file)
            if self._client_certificate_file and self._client_key_file
            else self._client_certificate_file
        )
        headers_string = environ.get(
            signal_config.headers_env_var,
            environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        )
        self._headers = headers or parse_env_headers(
            headers_string, liberal=True
        )
        self._timeout = timeout or float(
            environ.get(
                signal_config.timeout_env_var,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )
        self._compression = compression or _compression_from_env(
            signal_config.compression_env_var
        )
        combined_headers = {**_OTLP_HTTP_HEADERS, **self._headers}
        if self._compression is not Compression.NoCompression:
            combined_headers["Content-Encoding"] = self._compression.value
        self._client = _OTLPHTTPClient(
            endpoint=self._endpoint,
            certificate_file=self._certificate_file,
            client_key_file=self._client_key_file,
            client_certificate_file=self._client_certificate_file,
            timeout=self._timeout,
            headers=combined_headers,
        )
        self._shutdown = False
        self._metrics = ExporterMetrics(
            signal_config.metrics_component_type,
            signal_config.metrics_signal,
            urlparse(self._endpoint),
            meter_provider,
        )

    def _export(
        self, serialized_data: bytes, timeout_sec: Optional[float] = None
    ):
        data = serialized_data
        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with gzip.GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
                gzip_stream.write(serialized_data)
            data = gzip_data.getvalue()
        elif self._compression == Compression.Deflate:
            data = zlib.compress(serialized_data)

        if timeout_sec is None:
            timeout_sec = self._timeout

        return self._client.post(data, timeout_sec)

    def _export_with_retry(
        self,
        serialized_data: bytes,
        num_items: int,
        signal_name: str,
    ) -> bool:
        with self._metrics.export_operation(num_items) as result:
            deadline_sec = time() + self._timeout
            for retry_num in range(_MAX_RETRYS):
                # multiplying by a random number between .8 and 1.2 introduces a +/20% jitter to each backoff.
                backoff_seconds = 2**retry_num * random.uniform(0.8, 1.2)
                export_error: Optional[Exception] = None
                try:
                    resp = self._export(serialized_data, deadline_sec - time())
                    if resp.ok:
                        return True
                except OSError as error:
                    reason = error
                    export_error = error
                    retryable = isinstance(error, ConnectionError)
                    status_code = None
                else:
                    reason = resp.reason
                    retryable = _is_retryable(resp)
                    status_code = resp.status_code

                error_attrs = (
                    {HTTP_RESPONSE_STATUS_CODE: status_code}
                    if status_code is not None
                    else None
                )
                if not retryable:
                    _logger.error(
                        "Failed to export %s batch code: %s, reason: %s",
                        signal_name,
                        status_code,
                        reason,
                    )
                    result.error = export_error
                    result.error_attrs = error_attrs
                    return False

                if (
                    retry_num + 1 == _MAX_RETRYS
                    or backoff_seconds > (deadline_sec - time())
                    or self._shutdown
                ):
                    _logger.error(
                        "Failed to export %s batch due to timeout, "
                        "max retries or shutdown.",
                        signal_name,
                    )
                    result.error = export_error
                    result.error_attrs = error_attrs
                    return False

                _logger.warning(
                    "Transient error %s encountered while exporting %s batch, retrying in %.2fs.",
                    reason,
                    signal_name,
                    backoff_seconds,
                )
                if self._shutdown_in_progress.wait(backoff_seconds):
                    _logger.warning("Shutdown in progress, aborting retry.")
                    break
            return False

    def _do_shutdown(self):
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_in_progress.set()
        self._client.close()
