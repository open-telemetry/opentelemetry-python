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

import logging
import threading
from os import environ
from typing import Dict, Optional, Sequence
from urllib.parse import urlparse

import requests

from opentelemetry.exporter.otlp.proto.common._exporter_metrics import (
    ExporterMetrics,
)
from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp.proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.exporter.otlp.proto.http._common import (
    _load_session_from_envvar,
)
from opentelemetry.exporter.otlp.proto.http._otlp_client import (
    OTLPHTTPClient,
)
from opentelemetry.exporter.otlp.proto.http._transport import (
    BaseHTTPTransport,
)
from opentelemetry.exporter.otlp.proto.http._transport._requests import (
    RequestsHTTPTransport,
)
from opentelemetry.exporter.otlp.proto.http._transport._urllib3 import (
    Urllib3HTTPTransport,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER,
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
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.semconv.attributes.http_attributes import (
    HTTP_RESPONSE_STATUS_CODE,
)
from opentelemetry.util.re import parse_env_headers

_logger = logging.getLogger(__name__)


DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_TRACES_EXPORT_PATH = "v1/traces"
DEFAULT_TIMEOUT = 10  # in seconds


class OTLPSpanExporter(SpanExporter):
    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        client_key_file: Optional[str] = None,
        client_certificate_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        compression: Optional[Compression] = None,
        session: Optional[requests.Session] = None,
        *,
        meter_provider: Optional[MeterProvider] = None,
        _transport: Optional[BaseHTTPTransport] = None,
    ):
        self._shutdown_in_progress = threading.Event()
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
        self._timeout = timeout or float(
            environ.get(
                OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )
        self._compression = compression or _compression_from_env()

        if _transport is not None:
            transport: BaseHTTPTransport = _transport
        else:
            legacy_session = session or _load_session_from_envvar(
                _OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER
            )
            if legacy_session is not None:
                transport = RequestsHTTPTransport(
                    verify=self._certificate_file,
                    cert=self._client_cert,
                    session=legacy_session,
                )
            else:
                transport = Urllib3HTTPTransport(
                    verify=self._certificate_file,
                    cert=self._client_cert,
                )

        client_headers: dict[str, str] = {
            **_OTLP_HTTP_HEADERS,
            **self._headers,
        }
        if self._compression is not Compression.NoCompression:
            client_headers["Content-Encoding"] = self._compression.value

        self._client = OTLPHTTPClient(
            transport=transport,
            endpoint=self._endpoint,
            timeout=self._timeout,
            compression=self._compression,
            shutdown_event=self._shutdown_in_progress,
            headers=client_headers,
            kind="span",
        )
        self._shutdown = False

        self._metrics = ExporterMetrics(
            OtelComponentTypeValues.OTLP_HTTP_SPAN_EXPORTER,
            "traces",
            urlparse(self._endpoint),
            meter_provider,
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        with self._metrics.export_operation(len(spans)) as result:
            serialized_data = encode_spans(spans).SerializePartialToString()
            export_result = self._client.export(serialized_data)
            if export_result.success:
                return SpanExportResult.SUCCESS

            result.error = export_result.error
            if export_result.status_code is not None:
                result.error_attrs = {
                    HTTP_RESPONSE_STATUS_CODE: export_result.status_code
                }
            return SpanExportResult.FAILURE

    def shutdown(self):
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_in_progress.set()
        self._client.close()

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
