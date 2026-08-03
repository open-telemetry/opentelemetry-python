# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import os
from collections.abc import Sequence
from gzip import GzipFile
from io import BytesIO
from logging import getLogger
from os import environ
from random import uniform
from threading import Event
from time import time
from urllib.error import URLError
from urllib.parse import urlparse
from zlib import compress

from opentelemetry.exporter.otlp._proto.common._exporter_metrics import (
    create_exporter_metrics,
)
from opentelemetry.exporter.otlp._proto.common._internal.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp._proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.exporter.otlp._proto.http._common import (
    _build_ssl_context,
    _is_retryable,
    _post,
)
from opentelemetry.metrics import MeterProvider
from opentelemetry.sdk.environment_variables import (
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
from opentelemetry.util.re import parse_env_headers

_logger = getLogger(__name__)

DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_TRACES_EXPORT_PATH = "v1/traces"
DEFAULT_TIMEOUT = 10
_MAX_RETRYS = 6


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
        session: object | None = None,
        *,
        meter_provider: MeterProvider | None = None,
    ):
        if session is not None:
            _logger.warning(
                "session is not supported by the pure-Python OTLP HTTP "
                "exporter and will be ignored"
            )
        self._shutdown_in_progress = Event()
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
        self._headers = headers or parse_env_headers(headers_string, liberal=True)
        self._timeout = timeout or float(
            environ.get(
                OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )
        self._compression = compression or _compression_from_env()
        self._request_headers = {**_OTLP_HTTP_HEADERS, **self._headers}
        if self._compression is not Compression.NoCompression:
            self._request_headers["Content-Encoding"] = self._compression.value
        self._ssl_context = _build_ssl_context(
            self._certificate_file, self._client_cert
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

    def _export(self, serialized_data: bytes, timeout_sec: float | None = None):
        data = serialized_data
        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
                gzip_stream.write(serialized_data)
            data = gzip_data.getvalue()
        elif self._compression == Compression.Deflate:
            data = compress(serialized_data)
        if timeout_sec is None:
            timeout_sec = self._timeout
        try:
            return _post(
                self._endpoint,
                data,
                self._request_headers,
                timeout_sec,
                self._ssl_context,
            )
        except URLError:
            return _post(
                self._endpoint,
                data,
                self._request_headers,
                timeout_sec,
                self._ssl_context,
            )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE

        with self._metrics.export_operation(len(spans)) as result:
            serialized_data = encode_spans(spans).SerializeToString()
            deadline_sec = time() + self._timeout
            for retry_num in range(_MAX_RETRYS):
                backoff_seconds = 2**retry_num * uniform(0.8, 1.2)
                export_error: Exception | None = None
                try:
                    status_code, reason = self._export(
                        serialized_data, deadline_sec - time()
                    )
                    if status_code < 400:
                        return SpanExportResult.SUCCESS
                    retryable = _is_retryable(status_code)
                except URLError as error:
                    reason = error.reason
                    export_error = error
                    retryable = True
                    status_code = None

                if not retryable:
                    _logger.error(
                        "Failed to export span batch code: %s, reason: %s",
                        status_code,
                        reason,
                    )
                    error_attrs = (
                        {HTTP_RESPONSE_STATUS_CODE: status_code}
                        if status_code is not None
                        else None
                    )
                    result.error = export_error
                    result.error_attrs = error_attrs
                    return SpanExportResult.FAILURE

                if (
                    retry_num + 1 == _MAX_RETRYS
                    or backoff_seconds > (deadline_sec - time())
                    or self._shutdown
                ):
                    _logger.error(
                        "Failed to export span batch due to timeout, max retries or shutdown."
                    )
                    error_attrs = (
                        {HTTP_RESPONSE_STATUS_CODE: status_code}
                        if status_code is not None
                        else None
                    )
                    result.error = export_error
                    result.error_attrs = error_attrs
                    return SpanExportResult.FAILURE

                _logger.warning(
                    "Transient error %s encountered while exporting span batch, retrying in %.2fs.",
                    reason,
                    backoff_seconds,
                )
                if self._shutdown_in_progress.wait(backoff_seconds):
                    _logger.warning("Shutdown in progress, aborting retry.")
                    break
            return SpanExportResult.FAILURE

    def shutdown(self):
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._shutdown_in_progress.set()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def _compression_from_env() -> Compression:
    return Compression(
        environ.get(
            OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
            environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )


def _append_trace_path(endpoint: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + DEFAULT_TRACES_EXPORT_PATH
    return endpoint + f"/{DEFAULT_TRACES_EXPORT_PATH}"
