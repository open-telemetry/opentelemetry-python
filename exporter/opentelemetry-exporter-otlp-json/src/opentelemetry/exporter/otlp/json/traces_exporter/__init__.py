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

import gzip
import logging
import zlib
from io import BytesIO
from collections import defaultdict
from os import environ
from typing import Dict, Optional, Sequence
import json

import requests

from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.exporter.otlp.json import (
    _OTLP_HTTP_HEADERS,
    DEFAULT_ENDPOINT,
    Compression,
)
from opentelemetry.util.re import parse_env_headers

_logger = logging.getLogger(__name__)

DEFAULT_COMPRESSION = Compression.NoCompression
DEFAULT_ENDPOINT = "http://localhost:4318/"
DEFAULT_TRACES_EXPORT_PATH = "v1/traces"
DEFAULT_TIMEOUT = 10  # in seconds
REQUESTS_SUCCESS_STATUS_CODES = (200, 202)

logger = logging.getLogger(__name__)


class OTLPSpanExporter(SpanExporter):
    def __init__(
        self,
        endpoint: Optional[str] = None,
        certificate_file: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        compression: Optional[Compression] = None,
        session: Optional[requests.Session] = None,
    ):
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
        headers_string = environ.get(
            OTEL_EXPORTER_OTLP_TRACES_HEADERS,
            environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
        )
        self._headers = headers or parse_env_headers(headers_string)
        self._timeout = timeout or int(
            environ.get(
                OTEL_EXPORTER_OTLP_TRACES_TIMEOUT,
                environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
            )
        )
        self._compression = compression or _compression_from_env()
        self._session = session or requests.Session()
        self._session.headers.update(self._headers)
        self._session.headers.update(_OTLP_HTTP_HEADERS)
        if self._compression is not Compression.NoCompression:
            self._session.headers.update(
                {"Content-Encoding": self._compression.value}
            )
        self._shutdown = False


    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        # After the call to Shutdown subsequent calls to Export are
        # not allowed and should return a Failure result
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring batch")
            return SpanExportResult.FAILURE
        
        serialized_data = self._serialize_spans(spans)
        resp = self._export(serialized_data)

        #TODO: add retry logic / backoff - see otlp-proto-http for example
        if resp.ok:
            return SpanExportResult.SUCCESS
        
        _logger.error(
            "Failed to export batch code: %s, reason: %s",
            resp.status_code,
            resp.text,
        )
        return SpanExportResult.FAILURE


    def shutdown(self) -> None:
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring call")
            return
        self.session.close()
        self._shutdown = True

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Nothing is buffered in this exporter, so this method does nothing."""
        return True
    
    def _export(self, serialized_data: str):
        data = serialized_data
        if self._compression == Compression.Gzip:
            gzip_data = BytesIO()
            with gzip.GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
                gzip_stream.write(serialized_data)
            data = gzip_data.getvalue()
        elif self._compression == Compression.Deflate:
            data = zlib.compress(bytes(serialized_data))

        return self._session.post(
            url=self._endpoint,
            data=data,
            verify=self._certificate_file,
            timeout=self._timeout,
        )

    def _serialize_spans(self, sdk_spans: Sequence[ReadableSpan]) -> str:
        # We need to inspect the spans and group + structure them as:
        #
        #   Resource
        #     Instrumentation Scope
        #       Spans
        #
        # First loop organizes the SDK spans in this structure.
        #
        # Second loop encodes the data into JSON format.
        #

        sdk_resource_spans = defaultdict(lambda: defaultdict(list))
        for sdk_span in sdk_spans:
            sdk_resource = sdk_span.resource
            sdk_instrumentation = sdk_span.instrumentation_scope
            sdk_resource_spans[sdk_resource][sdk_instrumentation].append(sdk_span)

        resource_spans = []
        for sdk_resource, sdk_instrumentations in sdk_resource_spans.items():
            scope_spans = []
            for sdk_instrumentation, sdk_spans in sdk_instrumentations.items():
                scope_spans.append(
                    {
                        "scope": json.loads(sdk_instrumentation[0].to_json()),
                        "spans": [json.loads(sdk_span.to_json()) for sdk_span in sdk_spans],
                    }
                )
            resource_spans.append(
                {
                    "resource": json.loads(sdk_resource.to_json()),
                    "scope_spans": scope_spans,
                }
            )

        data = {
            "resource_spans": resource_spans
        }
        return json.dumps(data)


def _compression_from_env() -> Compression:
    compression = (
        environ.get(
            OTEL_EXPORTER_OTLP_TRACES_COMPRESSION,
            environ.get(OTEL_EXPORTER_OTLP_COMPRESSION, "none"),
        )
        .lower()
        .strip()
    )
    return Compression(compression)


def _append_trace_path(endpoint: str) -> str:
    if endpoint.endswith("/"):
        return endpoint + DEFAULT_TRACES_EXPORT_PATH
    return endpoint + f"/{DEFAULT_TRACES_EXPORT_PATH}"
