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
from collections.abc import Sequence
from os import environ

from opentelemetry.exporter.otlp.json.common.trace_encoder import encode_spans
from opentelemetry.exporter.otlp.json.http import Compression
from opentelemetry.exporter.otlp.json.http._internal import (
    _OTLPHttpClient,
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_timeout,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
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

_logger = logging.getLogger(__name__)

DEFAULT_TRACES_EXPORT_PATH = "v1/traces"


class OTLPSpanExporter(SpanExporter):
    def __init__(
        self,
        endpoint: str | None = None,
        certificate_file: str | None = None,
        client_key_file: str | None = None,
        client_certificate_file: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        compression: Compression | None = None,
    ):
        self._shutdown = False
        self._certificate_file = certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE),
        )
        self._client_key_file = client_key_file or environ.get(
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY),
        )
        self._client_certificate_file = client_certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
            environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE),
        )
        self._client = _OTLPHttpClient(
            endpoint=endpoint
            or _resolve_endpoint(
                OTEL_EXPORTER_OTLP_TRACES_ENDPOINT, DEFAULT_TRACES_EXPORT_PATH
            ),
            headers=_resolve_headers(
                headers, OTEL_EXPORTER_OTLP_TRACES_HEADERS
            ),
            timeout=_resolve_timeout(
                timeout, OTEL_EXPORTER_OTLP_TRACES_TIMEOUT
            ),
            compression=_resolve_compression(
                compression, OTEL_EXPORTER_OTLP_TRACES_COMPRESSION
            ),
            certificate=self._certificate_file,
            client_key_file=self._client_key_file,
            client_certificate_file=self._client_certificate_file,
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE
        body = encode_spans(spans).to_json().encode()
        if self._client.export(body):
            return SpanExportResult.SUCCESS
        return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._client.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True
