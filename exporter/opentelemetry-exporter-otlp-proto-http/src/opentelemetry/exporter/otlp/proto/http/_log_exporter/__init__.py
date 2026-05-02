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

from __future__ import annotations

import logging
import threading
from os import environ
from typing import (
    TYPE_CHECKING,
    Dict,
    Final,
    Literal,
    Optional,
    Sequence,
    overload,
)
from urllib.parse import urlparse

from opentelemetry.exporter.otlp.proto.common._exporter_metrics import (
    ExporterMetrics,
)
from opentelemetry.exporter.otlp.proto.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.proto.http import (
    _CONTENT_ENCODING_HEADER,
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.exporter.otlp.proto.http._common import (
    _compression_from_env,
    _endpoint_from_env,
    _session_from_env,
    _transport_from_args,
)
from opentelemetry.exporter.otlp.proto.http._otlp_client import (
    OTLPHTTPClient,
)
from opentelemetry.exporter.otlp.proto.http._transport import (
    BaseHTTPTransport,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    LogRecordExportResult,
)
from opentelemetry.sdk._shared_internal import DuplicateFilter
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER,
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.semconv.attributes.http_attributes import (
    HTTP_RESPONSE_STATUS_CODE,
)
from opentelemetry.util.re import parse_env_headers

if TYPE_CHECKING:
    import requests

_logger = logging.getLogger(__name__)
# This prevents logs generated when a log fails to be written to generate another log which fails to be written etc. etc.
_logger.addFilter(DuplicateFilter())


DEFAULT_TIMEOUT: Final[int] = 10  # in seconds
DEFAULT_LOGS_EXPORT_PATH: Final[Literal["v1/logs"]] = "v1/logs"


class OTLPLogExporter(LogRecordExporter):
    @overload
    def __init__(
        self,
        endpoint: str | None = ...,
        certificate_file: str | None = ...,
        client_key_file: str | None = ...,
        client_certificate_file: str | None = ...,
        headers: dict[str, str] | None = ...,
        timeout: float | None = ...,
        compression: Compression | None = ...,
        session: requests.Session | None = ...,
        *,
        meter_provider: MeterProvider | None = ...,
        _transport: None = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        endpoint: str | None = ...,
        certificate_file: str | None = ...,
        client_key_file: str | None = ...,
        client_certificate_file: str | None = ...,
        headers: dict[str, str] | None = ...,
        timeout: float | None = ...,
        compression: Compression | None = ...,
        session: None = ...,
        *,
        meter_provider: MeterProvider | None = ...,
        _transport: BaseHTTPTransport,
    ) -> None: ...

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
        self._shutdown_event = threading.Event()
        self._endpoint = endpoint or _endpoint_from_env(
            OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, DEFAULT_LOGS_EXPORT_PATH
        )
        # Keeping these as instance variables because they are used in tests
        self._certificate_file = certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE, True),
        )
        self._client_key_file = client_key_file or environ.get(
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY, None),
        )
        self._client_certificate_file = client_certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE, None),
        )
        self._client_cert = (
            (self._client_certificate_file, self._client_key_file)
            if self._client_certificate_file and self._client_key_file
            else self._client_certificate_file
        )
        headers_string = environ.get(
            OTEL_EXPORTER_OTLP_LOGS_HEADERS,
            environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        )
        self._headers = headers or parse_env_headers(
            headers_string, liberal=True
        )
        self._timeout = timeout or float(
            environ.get(
                OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )
        self._compression = compression or _compression_from_env(
            OTEL_EXPORTER_OTLP_LOGS_COMPRESSION
        )

        transport = _transport or _transport_from_args(
            session
            or _session_from_env(
                _OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER
            ),
            self._certificate_file,
            self._client_cert,
        )

        client_headers: dict[str, str] = {
            **_OTLP_HTTP_HEADERS,
            **self._headers,
        }
        if self._compression is not Compression.NoCompression:
            client_headers[_CONTENT_ENCODING_HEADER] = self._compression.value

        self._client = OTLPHTTPClient(
            transport=transport,
            endpoint=self._endpoint,
            timeout=self._timeout,
            compression=self._compression,
            shutdown_event=self._shutdown_event,
            headers=client_headers,
            kind="logs",
        )
        self._shutdown = False

        self._metrics = ExporterMetrics(
            OtelComponentTypeValues.OTLP_HTTP_LOG_EXPORTER,
            "logs",
            urlparse(self._endpoint),
            meter_provider,
        )

    def export(
        self, batch: Sequence[ReadableLogRecord]
    ) -> LogRecordExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return LogRecordExportResult.FAILURE

        with self._metrics.export_operation(len(batch)) as result:
            serialized_data = encode_logs(batch).SerializeToString()
            export_result = self._client.export(serialized_data)
            if export_result.success:
                return LogRecordExportResult.SUCCESS

            result.error = export_result.error
            if export_result.status_code is not None:
                result.error_attrs = {
                    HTTP_RESPONSE_STATUS_CODE: export_result.status_code
                }
            return LogRecordExportResult.FAILURE

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True

    def shutdown(self):
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_event.set()
        self._client.close()
