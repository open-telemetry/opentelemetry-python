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
from typing import Dict, Optional, Sequence

import requests

from opentelemetry.exporter.otlp.proto.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.proto.http import (
    Compression,
)
from opentelemetry.exporter.otlp.proto.http._common import (
    OTLPHttpClient,
    _SignalConfig,
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
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
)
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)

_logger = logging.getLogger(__name__)
# This prevents logs generated when a log fails to be written to generate another log which fails to be written etc. etc.
_logger.addFilter(DuplicateFilter())

DEFAULT_LOGS_EXPORT_PATH = "v1/logs"

_LOGS_CONFIG = _SignalConfig(
    endpoint_envvar=OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    certificate_envvar=OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    client_key_envvar=OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
    client_certificate_envvar=OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    headers_envvar=OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    timeout_envvar=OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
    compression_envvar=OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    credential_envvar=_OTEL_PYTHON_EXPORTER_OTLP_HTTP_LOGS_CREDENTIAL_PROVIDER,
    default_export_path=DEFAULT_LOGS_EXPORT_PATH,
    component_type=OtelComponentTypeValues.OTLP_HTTP_LOG_EXPORTER,
    signal_name="logs",
)


class OTLPLogExporter(OTLPHttpClient, LogRecordExporter):
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
    ):
        OTLPHttpClient.__init__(
            self,
            endpoint=endpoint,
            certificate_file=certificate_file,
            client_key_file=client_key_file,
            client_certificate_file=client_certificate_file,
            headers=headers,
            timeout=timeout,
            compression=compression,
            session=session,
            meter_provider=meter_provider,
            signal_config=_LOGS_CONFIG,
        )

    def export(
        self, batch: Sequence[ReadableLogRecord]
    ) -> LogRecordExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return LogRecordExportResult.FAILURE

        serialized_data = encode_logs(batch).SerializeToString()
        with self._metrics.export_operation(len(batch)) as result:
            success = self._export_with_retries(
                serialized_data, result, "logs"
            )
        return (
            LogRecordExportResult.SUCCESS
            if success
            else LogRecordExportResult.FAILURE
        )

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True
