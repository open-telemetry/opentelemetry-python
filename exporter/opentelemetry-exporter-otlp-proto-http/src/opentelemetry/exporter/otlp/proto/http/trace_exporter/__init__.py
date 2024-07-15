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
import zlib
from io import BytesIO
from os import environ
from typing import Dict, Optional

import requests

from opentelemetry.exporter.otlp.proto.common.exporter import (
    RetryableExportError,
    RetryingExporter,
)
from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.exporter.otlp.proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.util.re import parse_env_headers


_logger = logging.getLogger(__name__)


DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_TRACES_EXPORT_PATH = "v1/traces"
DEFAULT_TIMEOUT = 10  # in seconds


class OTLPSpanExporter(SpanExporter):

    _MAX_RETRY_TIMEOUT = 64

    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        client_key_file: Optional[str] = None,
        client_certificate_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        session: Optional[requests.Session] = None,
    ):
        self._endpoint = endpoint or environ.get(
            OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
            _append_trace_path(
                environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, DEFAULT_ENDPOINT)
            ),
        )
        self._certificate_file = certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE, True),
        )
        self._client_key_file = client_key_file or environ.get(
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY, None),
        )
        self._client_certificate_file = client_certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE, None),
        )
        self._client_cert = (
            (self._client_certificate_file, self._client_key_file)
            if self._client_certificate_file and self._client_key_file
            else self._client_certificate_file
        )
        headers_string = environ.get(
            OTEL_EXPORTER_OTLP_TRACES_HEADERS,
            environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        )
        self._headers = headers or parse_env_headers(
            headers_string, liberal=True
        )
        self._timeout = timeout or int(
            environ.get(
                OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )
        self._compression = compression or _compression_from_env()
        self._session = session or requests.Session()
        self._session.headers.update(self._headers)
        self._session.headers.update(_OTLP_HTTP_HEADERS)
        if self._compression is not Compression.NoCompression:
            self._session.headers.update(
                {"Content-Encoding": self._compression.value}
            )
        self._shutdown = False
        self._exporter = RetryingExporter(self._export, SpanExportResult)

    def _export(self, serialized_data: bytes):
        data = serialized_data
        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with gzip.GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
                gzip_stream.write(serialized_data)
            data = gzip_data.getvalue()
        elif self._compression == Compression.Deflate:
            data = zlib.compress(serialized_data)

        resp = self._session.post(
            url=self._endpoint,
            data=data,
            verify=self._certificate_file,
            timeout=self._timeout,
            cert=self._client_cert,
        )

        if resp.ok:
            return SpanExportResult.SUCCESS

        if self._retryable(resp):
            _logger.warning(
                "Transient error %s encountered while exporting span batch",
                resp.reason,
            )
            raise RetryableExportError(None)

        _logger.error(
            "Failed to export batch code: %s, reason: %s",
            resp.status_code,
            resp.text,
        )
        return SpanExportResult.FAILURE

    @staticmethod
    def _retryable(resp: requests.Response) -> bool:
        if resp.status_code == 408:
            return True
        if resp.status_code >= 500 and resp.status_code <= 599:
            return True
        return False

    def _serialize_spans(self, spans):
        return encode_spans(spans).SerializePartialToString()

    def export(self, spans) -> SpanExportResult:
        # After the call to Shutdown subsequent calls to Export are
        # not allowed and should return a Failure result.
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        serialized_data = self._serialize_spans(spans)
        return self._exporter.export_with_retry(serialized_data)

    def shutdown(self):
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._session.close()
        self._shutdown = True

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True


def _compression_from_env() -> Compression:
    compression = (
        environ.get(
            OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
            environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )
    return Compression(compression)


def _append_trace_path(endpoint: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + DEFAULT_TRACES_EXPORT_PATH
    return endpoint + f"/{DEFAULT_TRACES_EXPORT_PATH}"
