# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, overload
from urllib.parse import urlparse

import requests

from opentelemetry.exporter.otlp.common._http import (
    Compression as CommonCompression,
)
from opentelemetry.exporter.otlp.common._http import OTLPHTTPClient
from opentelemetry.exporter.otlp.proto.common._exporter_metrics import (
    create_exporter_metrics,
)
from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp.proto.http import Compression
from opentelemetry.exporter.otlp.proto.http._internal import (
    _build_transport,
    _normalize_compression,
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_session,
    _resolve_timeout,
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
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OtelComponentTypeValues,
)
from opentelemetry.semconv.attributes.http_attributes import (
    HTTP_RESPONSE_STATUS_CODE,
)

if TYPE_CHECKING:
    from opentelemetry.exporter.http.transport._base import BaseHTTPTransport

_logger = logging.getLogger(__name__)


DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_TRACES_EXPORT_PATH = "v1/traces"
DEFAULT_TIMEOUT = 10  # in seconds


class OTLPSpanExporter(SpanExporter):
    @overload
    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | CommonCompression | None = None,
        session: requests.Session | None = None,
        *,
        meter_provider: MeterProvider | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: None = None,
        client_key_file: None = None,
        client_certificate_file: None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | CommonCompression | None = None,
        session: requests.Session | None = None,
        *,
        meter_provider: MeterProvider | None = None,
        _transport: BaseHTTPTransport,
    ) -> None: ...

    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | CommonCompression | None = None,
        session: requests.Session | None = None,
        *,
        meter_provider: MeterProvider | None = None,
        _transport: BaseHTTPTransport | None = None,
    ) -> None:
        self._endpoint = endpoint or _resolve_endpoint(
            OTEL_EXPORTER_OTLP_TRACES_ENDPOINT, DEFAULT_TRACES_EXPORT_PATH
        )
        self._compression = _normalize_compression(
            compression
        ) or _resolve_compression(OTEL_EXPORTER_OTLP_TRACES_COMPRESSION)
        self._session = _resolve_session(
            session, _OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER
        )
        transport = _transport or _build_transport(
            certificate_file,
            client_key_file,
            client_certificate_file,
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
            session=self._session,
        )
        self._client = OTLPHTTPClient(
            transport=transport,
            endpoint=self._endpoint,
            kind="spans",
            timeout=timeout
            if timeout is not None
            else _resolve_timeout(OTEL_EXPORTER_OTLP_TRACES_TIMEOUT),
            compression=self._compression,
            headers=_resolve_headers(
                headers, OTEL_EXPORTER_OTLP_TRACES_HEADERS
            ),
            logger=_logger,
        )
        self._shutdown = False

        self._metrics = create_exporter_metrics(
            OtelComponentTypeValues.OTLP_HTTP_SPAN_EXPORTER,
            "traces",
            urlparse(self._endpoint),
            meter_provider,
            os.environ.get(OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED, "")
            .strip()
            .lower()
            == "true",
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        with self._metrics.export_operation(len(spans)) as result:
            try:
                serialized_data = encode_spans(spans).SerializePartialToString()
            # pylint: disable-next=broad-exception-caught
            except Exception as error:
                _logger.error("Failed to encode span batch: %s", error)
                result.error = error
                return SpanExportResult.FAILURE

            export_result = self._client.export(serialized_data)
            if not export_result.success:
                result.error = export_result.error
                result.error_attrs = (
                    {HTTP_RESPONSE_STATUS_CODE: export_result.status_code}
                    if export_result.status_code is not None
                    else None
                )
                return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS

    def shutdown(self):
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._client.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True
