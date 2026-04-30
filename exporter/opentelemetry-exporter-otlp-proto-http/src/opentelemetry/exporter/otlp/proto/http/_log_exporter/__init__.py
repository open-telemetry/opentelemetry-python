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
from typing import Sequence
from urllib.parse import urlparse

from opentelemetry.exporter.otlp.proto.common._exporter_metrics import (
    ExporterMetrics,
)
from opentelemetry.exporter.otlp.proto.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http._client import OTLPHttpClient
from opentelemetry.exporter.otlp.proto.http._common import (
    _build_default_headers,
    _load_session_from_envvar,
)
from opentelemetry.exporter.otlp.proto.http._session import (
    HttpSession,
    Urllib3Session,
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
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
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

_logger = logging.getLogger(__name__)
# This prevents logs generated when a log fails to be written to generate another log which fails to be written etc. etc.
_logger.addFilter(DuplicateFilter())


DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_LOGS_EXPORT_PATH = "v1/logs"
DEFAULT_TIMEOUT = 10  # in seconds


class OTLPLogExporter(LogRecordExporter):
    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
        session: HttpSession | None = None,
        *,
        meter_provider: MeterProvider | None = None,
    ):
        self._shutdown_is_occuring = threading.Event()
        self._endpoint = endpoint or environ.get(
            OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
            _append_logs_path(
                environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, DEFAULT_ENDPOINT)
            ),
        )
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
        self._compression = compression or _compression_from_env()

        session_ = session or _load_session_from_envvar(
            _OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER
        )

        self._session: HttpSession = session_ or Urllib3Session(
            verify=self._certificate_file,
            cert=self._client_cert,
        )
        self._client: OTLPHttpClient[HttpSession] = OTLPHttpClient(
            session=self._session,
            endpoint=self._endpoint,
            timeout=self._timeout,
            compression=self._compression,
            shutdown_event=self._shutdown_is_occuring,
            headers=_build_default_headers(
                self._headers, self._compression
            ),
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
            outcome = self._client.export(serialized_data)
            if outcome.success:
                return LogRecordExportResult.SUCCESS
            result.error = outcome.error
            result.error_attrs = (
                {HTTP_RESPONSE_STATUS_CODE: outcome.status_code}
                if outcome.status_code is not None
                else None
            )
            return LogRecordExportResult.FAILURE

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True

    def shutdown(self):
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_is_occuring.set()
        self._client.close()


def _compression_from_env() -> Compression:
    compression = (
        environ.get(
            OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
            environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )
    return Compression(compression)


def _append_logs_path(endpoint: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + DEFAULT_LOGS_EXPORT_PATH
    return endpoint + f"/{DEFAULT_LOGS_EXPORT_PATH}"
