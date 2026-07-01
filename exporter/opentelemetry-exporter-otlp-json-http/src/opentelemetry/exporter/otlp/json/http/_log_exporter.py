# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from collections.abc import Mapping, Sequence
from typing import overload

from opentelemetry.exporter.http.transport._base import BaseHTTPTransport
from opentelemetry.exporter.http.transport._urllib3 import Urllib3HTTPTransport
from opentelemetry.exporter.otlp.common import Compression
from opentelemetry.exporter.otlp.common._http import OTLPHTTPClient
from opentelemetry.exporter.otlp.json.common._internal._log_encoder import (
    encode_logs,
)
from opentelemetry.exporter.otlp.json.http._internal import (
    _resolve_compression,
    _resolve_endpoint,
    _resolve_headers,
    _resolve_timeout,
)
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    LogRecordExportResult,
)
from opentelemetry.sdk._shared_internal import DuplicateFilter
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_LOGS_COMPRESSION,
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
)

_DEFAULT_LOGS_EXPORT_PATH = "v1/logs"

_logger = logging.getLogger(__name__)
_logger.addFilter(DuplicateFilter())


class OTLPLogExporter(LogRecordExporter):
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
        certificate_file = certificate_file or os.environ.get(
            OTEL_EXPORTER_OTLP_LOGS_CERTIFICATE,
            os.environ.get(OTEL_EXPORTER_OTLP_CERTIFICATE, True),
        )
        client_key_file = client_key_file or os.environ.get(
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY,
            os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_KEY),
        )
        client_certificate_file = client_certificate_file or os.environ.get(
            OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE,
            os.environ.get(OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE),
        )
        transport = (
            _transport
            if _transport
            else Urllib3HTTPTransport(
                verify=certificate_file,
                cert=(client_certificate_file, client_key_file)
                if client_certificate_file and client_key_file
                else client_certificate_file,
            )
        )
        self._client = OTLPHTTPClient(
            transport=transport,
            endpoint=endpoint
            or _resolve_endpoint(
                OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, _DEFAULT_LOGS_EXPORT_PATH
            ),
            kind="logs",
            timeout=timeout
            if timeout is not None
            else _resolve_timeout(OTEL_EXPORTER_OTLP_LOGS_TIMEOUT),
            compression=compression
            if compression is not None
            else _resolve_compression(OTEL_EXPORTER_OTLP_LOGS_COMPRESSION),
            headers=_resolve_headers(headers, OTEL_EXPORTER_OTLP_LOGS_HEADERS),
            logger=_logger,
        )
        self._shutdown = False

    def export(
        self, batch: Sequence[ReadableLogRecord]
    ) -> LogRecordExportResult:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring batch")
            return LogRecordExportResult.FAILURE
        try:
            body = encode_logs(batch).to_json().encode()
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            _logger.error("Failed to encode logs: %s", error)
            return LogRecordExportResult.FAILURE
        export_result = self._client.export(body)
        return (
            LogRecordExportResult.SUCCESS
            if export_result.success
            else LogRecordExportResult.FAILURE
        )

    def shutdown(self) -> None:
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._client.shutdown()

    def force_flush(self, timeout_millis: int = 10_000) -> bool:
        return True
