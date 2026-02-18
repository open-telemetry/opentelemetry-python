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
from typing import Optional, Sequence

from opentelemetry.exporter.otlp.json.common._internal.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp.json.http import Compression
from opentelemetry.exporter.otlp.json.http._internal import (
    _OTLPHttpClient,
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_timeout,
    _resolve_tls_file,
    _DEFAULT_JITTER,
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
from opentelemetry.sdk.trace.export import (
    ReadableSpan,
    SpanExporter,
    SpanExportResult,
)

_logger = logging.getLogger(__name__)


class OTLPJSONTraceExporter(SpanExporter):
    """OTLP JSON exporter for traces using urllib3."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        client_key_file: Optional[str] = None,
        client_certificate_file: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        compression: Optional[Compression] = None,
        jitter: float = _DEFAULT_JITTER,
    ):
        self._endpoint = endpoint or _resolve_endpoint(
            "v1/traces", OTEL_EXPORTER_OTLP_TRACES_ENDPOINT
        )

        self._certificate_file = _resolve_tls_file(
            certificate_file,
            OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CERTIFICATE,
        )
        self._client_key_file = _resolve_tls_file(
            client_key_file,
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
            OTEL_EXPORTER_OTLP_CLIENT_KEY,
        )
        self._client_certificate_file = _resolve_tls_file(
            client_certificate_file,
            OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
            OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
        )

        self._headers = _resolve_headers(
            OTEL_EXPORTER_OTLP_TRACES_HEADERS, headers
        )

        self._timeout = _resolve_timeout(
            OTEL_EXPORTER_OTLP_TRACES_TIMEOUT, timeout
        )
        self._compression = _resolve_compression(
            OTEL_EXPORTER_OTLP_TRACES_COMPRESSION, compression
        )

        self._client = _OTLPHttpClient(
            endpoint=self._endpoint,
            headers=self._headers,
            timeout=self._timeout,
            compression=self._compression,
            certificate_file=self._certificate_file,
            client_key_file=self._client_key_file,
            client_certificate_file=self._client_certificate_file,
            jitter=jitter,
        )

    def export(
        self,
        spans: Sequence[ReadableSpan],
    ) -> SpanExportResult:
        encoded_request = encode_spans(spans)
        body = encoded_request.to_json().encode("utf-8")
        if self._client.export(body):
            return SpanExportResult.SUCCESS
        return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        self._client.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
