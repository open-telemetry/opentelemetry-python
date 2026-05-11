# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Sequence

import requests

from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp.proto.http import (
    Compression,
)
from opentelemetry.exporter.otlp.proto.http._common import (
    OTLPHttpClient,
    _SignalConfig,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER,
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

_logger = logging.getLogger(__name__)

DEFAULT_TRACES_EXPORT_PATH = "v1/traces"

_TRACES_CONFIG = _SignalConfig(
    endpoint_envvar=OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    certificate_envvar=OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    client_key_envvar=OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
    client_certificate_envvar=OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
    headers_envvar=OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    timeout_envvar=OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
    compression_envvar=OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    credential_envvar=_OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER,
    default_export_path=DEFAULT_TRACES_EXPORT_PATH,
    component_type=OtelComponentTypeValues.OTLP_HTTP_SPAN_EXPORTER,
    signal_name="traces",
)


class OTLPSpanExporter(OTLPHttpClient, SpanExporter):
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
            signal_config=_TRACES_CONFIG,
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        serialized_data = encode_spans(spans).SerializePartialToString()
        with self._metrics.export_operation(len(spans)) as result:
            return (
                SpanExportResult.SUCCESS
                if self._export_with_retries(serialized_data, result, "span")
                else SpanExportResult.FAILURE
            )

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True
