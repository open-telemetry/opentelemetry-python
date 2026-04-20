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

from opentelemetry.context import attach, detach, set_value
from opentelemetry.exporter.otlp.json.http._log_exporter import (
    OTLPLogExporter as JsonHttpLogExporter,
)
from opentelemetry.exporter.otlp.json.http.metric_exporter import (
    OTLPMetricExporter as JsonHttpMetricExporter,
)
from opentelemetry.exporter.otlp.json.http.trace_exporter import (
    OTLPSpanExporter as JsonHttpSpanExporter,
)
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter as GrpcLogExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter as GrpcMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as GrpcSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter as HttpLogExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as HttpMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HttpSpanExporter,
)
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

_JSON_HTTP_ENDPOINT = "http://localhost:4319"

TRACE_EXPORTERS = [
    ("grpc", lambda: GrpcSpanExporter(insecure=True, timeout=1)),
    ("proto-http", HttpSpanExporter),
    (
        "json-http",
        lambda: JsonHttpSpanExporter(
            endpoint=_JSON_HTTP_ENDPOINT + "/v1/traces"
        ),
    ),
]

METRIC_EXPORTERS = [
    ("grpc", lambda: GrpcMetricExporter(insecure=True, timeout=1)),
    ("proto-http", HttpMetricExporter),
    (
        "json-http",
        lambda: JsonHttpMetricExporter(
            endpoint=_JSON_HTTP_ENDPOINT + "/v1/metrics"
        ),
    ),
]

LOG_EXPORTERS = [
    ("grpc", lambda: GrpcLogExporter(insecure=True, timeout=1)),
    ("proto-http", HttpLogExporter),
    (
        "json-http",
        lambda: JsonHttpLogExporter(endpoint=_JSON_HTTP_ENDPOINT + "/v1/logs"),
    ),
]


class ExportStatusSpanProcessor(SimpleSpanProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.export_status = []

    def on_end(self, span):
        token = attach(set_value("suppress_instrumentation", True))
        self.export_status.append(self.span_exporter.export((span,)))
        detach(token)
