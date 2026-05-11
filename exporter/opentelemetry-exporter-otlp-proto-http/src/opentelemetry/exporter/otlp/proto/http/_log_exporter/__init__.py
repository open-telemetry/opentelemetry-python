# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Sequence

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
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
        session: requests.Session | None = None,
        *,
        meter_provider: MeterProvider | None = None,
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
            return (
                LogRecordExportResult.SUCCESS
                if self._export_with_retries(serialized_data, result, "logs")
                else LogRecordExportResult.FAILURE
            )

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True
