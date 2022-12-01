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
from os import environ
from typing import Dict, Optional, Sequence

import requests

from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk._logs.export import (
    LogExporter,
    LogExportResult,
    LogData,
)
from opentelemetry.exporter.otlp.proto.http import (
    _OTLP_HTTP_HEADERS,
    Compression,
)
from opentelemetry.exporter.otlp.proto.http.exporter import (
    OTLPExporterMixin, DEFAULT_COMPRESSION, DEFAULT_ENDPOINT, 
    DEFAULT_TIMEOUT, _expo, _compression_from_env
)

from opentelemetry.exporter.otlp.proto.http._log_exporter.encoder import (
    _ProtobufEncoder,
)
from opentelemetry.util.re import parse_headers


_logger = logging.getLogger(__name__)


DEFAULT_LOGS_EXPORT_PATH = "v1/logs"


class OTLPLogExporter(
    LogExporter, OTLPExporterMixin[LogData, LogExportResult]
):

    _MAX_RETRY_TIMEOUT = 64
    _result = LogExportResult
    _encoder = _ProtobufEncoder

    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        session: Optional[requests.Session] = None,
    ):
        self._endpoint = endpoint or _append_logs_path(
            environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, DEFAULT_ENDPOINT)
        )
        self._certificate_file = certificate_file or environ.get(
            OTEL_EXPORTER_OTLP_CERTIFICATE, True
        )
        headers_string = environ.get(OTEL_EXPORTER_OTLP_HEADERS, "")
        self._headers = headers or parse_headers(headers_string)
        self._timeout = timeout or int(
            environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT)
        )
        self._compression = compression or _compression_from_env(OTEL_EXPORTER_OTLP_COMPRESSION)
        self._session = session or requests.Session()
        self._session.headers.update(self._headers)
        self._session.headers.update(_OTLP_HTTP_HEADERS)
        if self._compression is not Compression.NoCompression:
            self._session.headers.update(
                {"Content-Encoding": self._compression.value}
            )
        self._shutdown = False
        OTLPExporterMixin.__init__(
            self,
            self._endpoint,
            self._certificate_file,
            self._headers,
            self._timeout,
            self._compression,
            self._session,
        )

    def export(self, batch: Sequence[LogData]) -> LogExportResult:
        return OTLPExporterMixin.export(self, batch)

    def shutdown(self):
        if self._shutdown:
            _logger.warning("Exporter already shutdown, ignoring call")
            return
        self._session.close()
        self._shutdown = True

def _append_logs_path(endpoint: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + DEFAULT_LOGS_EXPORT_PATH
    return endpoint + f"/{DEFAULT_LOGS_EXPORT_PATH}"
