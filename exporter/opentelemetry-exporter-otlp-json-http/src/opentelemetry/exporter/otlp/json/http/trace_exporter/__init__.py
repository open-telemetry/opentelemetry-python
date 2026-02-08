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
import os
import random
import threading
import time
import zlib
from io import BytesIO
from typing import Dict, Optional, Sequence

import urllib3
from urllib3 import BaseHTTPResponse

from opentelemetry.exporter.otlp.json.common._internal.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp.json.http import Compression
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
)
from opentelemetry.sdk.trace.export import (
    ReadableSpan,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.util.re import parse_env_headers

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_TRACES_EXPORT_PATH = "v1/traces"
DEFAULT_TIMEOUT = 10
_MAX_RETRYS = 6


class OTLPJSONTraceExporter(SpanExporter):
    """OTLP JSON exporter for traces using urllib3."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        client_key_file: Optional[str] = None,
        client_certificate_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        compression: Optional[Compression] = None,
        jitter: float = 0.2,
    ):
        self._shutdown_in_progress = threading.Event()
        self._shutdown = False
        self._jitter = jitter
        self._endpoint = endpoint or os.environ.get(
            OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
            _append_trace_path(
                os.environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, DEFAULT_ENDPOINT)
            ),
        )

        self._certificate_file = certificate_file or os.environ.get(
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
            os.environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE, None),
        )
        self._client_key_file = client_key_file or os.environ.get(
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
            os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY, None),
        )
        self._client_certificate_file = (
            client_certificate_file
            or os.environ.get(
                OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
                os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE, None),
            )
        )

        headers_string = os.environ.get(
            OTEL_EXPORTER_OTLP_TRACES_HEADERS,
            os.environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        )
        self._headers = {"Content-Type": "application/json"}
        self._headers.update(
            headers or parse_env_headers(headers_string, liberal=True)
        )

        self._timeout = timeout or float(
            os.environ.get(
                OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
                os.environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )

        self._compression = compression or _compression_from_env()
        if self._compression is not Compression.NoCompression:
            self._headers.update({"Content-Encoding": self._compression.value})

        self._http = urllib3.PoolManager(
            retries=False,
            ca_certs=self._certificate_file,
            cert_file=self._client_certificate_file,
            key_file=self._client_key_file,
        )

    def _export(
        self, body: bytes, timeout_sec: Optional[float] = None
    ) -> BaseHTTPResponse:
        return self._http.request(
            "POST",
            self._endpoint,
            body=body,
            headers=self._headers,
            timeout=timeout_sec if timeout_sec is not None else self._timeout,
            retries=False,
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        encoded_request = encode_spans(spans)
        body = encoded_request.to_json().encode("utf-8")

        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with gzip.GzipFile(fileobj=gzip_data, mode="wb") as gzip_stream:
                gzip_stream.write(body)
            body = gzip_data.getvalue()
        elif self._compression == Compression.Deflate:
            body = zlib.compress(body)

        deadline_sec = time.time() + self._timeout
        for retry_num in range(_MAX_RETRYS):
            backoff_seconds = self._get_backoff_with_jitter(retry_num)
            try:
                response = self._export(body, deadline_sec - time.time())
                if 200 <= response.status < 300:
                    return SpanExportResult.SUCCESS

                retryable = _is_retryable(response.status)
                reason = response.status
            except Exception as error:
                retryable = True
                reason = error

            if not retryable:
                _logger.error(
                    "Failed to export span batch code: %s",
                    reason,
                )
                return SpanExportResult.FAILURE

            if (
                retry_num + 1 == _MAX_RETRYS
                or backoff_seconds > (deadline_sec - time.time())
                or self._shutdown
            ):
                _logger.error(
                    "Failed to export span batch due to timeout, "
                    "max retries or shutdown."
                )
                return SpanExportResult.FAILURE

            _logger.warning(
                "Transient error %s encountered while exporting span batch, retrying in %.2fs.",
                reason,
                backoff_seconds,
            )
            shutdown = self._shutdown_in_progress.wait(backoff_seconds)
            if shutdown:
                _logger.warning("Shutdown in progress, aborting retry.")
                break

        return SpanExportResult.FAILURE

    def _get_backoff_with_jitter(self, retry_num: int) -> float:
        """Calculate jittered exponential backoff."""
        base_backoff = 2**retry_num
        if self._jitter == 0:
            return float(base_backoff)
        return base_backoff * random.uniform(
            1 - self._jitter, 1 + self._jitter
        )

    def shutdown(self) -> None:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_in_progress.set()
        self._http.clear()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def _is_retryable(status_code: int) -> bool:
    return status_code in (408, 429) or (500 <= status_code < 600)


def _compression_from_env() -> Compression:
    compression = (
        os.environ.get(
            OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
            os.environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )
    try:
        return Compression(compression)
    except ValueError:
        _logger.warning("Unsupported compression type: %s", compression)
        return Compression.NoCompression


def _append_trace_path(endpoint: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + DEFAULT_TRACES_EXPORT_PATH
    return endpoint + f"/{DEFAULT_TRACES_EXPORT_PATH}"
