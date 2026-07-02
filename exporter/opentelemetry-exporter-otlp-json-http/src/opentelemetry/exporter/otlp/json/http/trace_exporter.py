# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
from collections.abc import Mapping, Sequence
from typing import overload

from opentelemetry.exporter.http.transport._base import BaseHTTPTransport
from opentelemetry.exporter.otlp.common.http import (
    Compression,
    _OTLPHTTPClient,
)
from opentelemetry.exporter.otlp.json.common._internal.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp.json.http._internal import (
    _build_transport,
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_timeout,
)
from opentelemetry.sdk.environment_variables import (
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

_DEFAULT_TRACES_EXPORT_PATH = "v1/traces"

_logger = logging.getLogger(__name__)


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
        compression: Compression | None = None,
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
        compression: Compression | None = None,
        *,
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
        compression: Compression | None = None,
        *,
        _transport: BaseHTTPTransport | None = None,
    ) -> None:
        transport = _transport or _build_transport(
            certificate_file,
            client_key_file,
            client_certificate_file,
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
        )
        self._client = _OTLPHTTPClient(
            transport=transport,
            endpoint=endpoint
            or _resolve_endpoint(
                OTEL_EXPORTER_OTLP_TRACES_ENDPOINT, _DEFAULT_TRACES_EXPORT_PATH
            ),
            kind="spans",
            timeout=timeout
            if timeout is not None
            else _resolve_timeout(OTEL_EXPORTER_OTLP_TRACES_TIMEOUT),
            compression=compression
            if compression is not None
            else _resolve_compression(OTEL_EXPORTER_OTLP_TRACES_COMPRESSION),
            headers=_resolve_headers(
                headers, OTEL_EXPORTER_OTLP_TRACES_HEADERS
            ),
            logger=_logger,
        )
        self._shutdown = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE
        try:
            body = encode_spans(spans).to_json().encode()
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            _logger.error("Failed to encode spans: %s", error)
            return SpanExportResult.FAILURE
        export_result = self._client.export(body)
        return (
            SpanExportResult.SUCCESS
            if export_result.success
            else SpanExportResult.FAILURE
        )

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._client.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
