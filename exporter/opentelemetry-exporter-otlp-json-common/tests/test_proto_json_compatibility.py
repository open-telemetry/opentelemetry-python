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

"""Tests verifying compatibility between opentelemetry-exporter-otlp-json-common
and protobuf's built-in JSON serialization (MessageToDict / ParseDict).

OTLP JSON deviations from standard proto3 JSON mapping:
- traceId/spanId/parentSpanId: hex-encoded (not base64)
- Enum fields: integer values only
- Keys: lowerCamelCase
- 64-bit integers: string-encoded
"""

import base64
import unittest
from typing import Any

from google.protobuf.json_format import MessageToDict, ParseDict

from opentelemetry._logs import SeverityNumber
from opentelemetry.exporter.otlp.json.common._log_encoder import (
    encode_logs as json_encode_logs,
)
from opentelemetry.exporter.otlp.json.common.metrics_encoder import (
    encode_metrics as json_encode_metrics,
)
from opentelemetry.exporter.otlp.json.common.trace_encoder import (
    encode_spans as json_encode_spans,
)
from opentelemetry.exporter.otlp.proto.common._log_encoder import (
    encode_logs as proto_encode_logs,
)
from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics as proto_encode_metrics,
)
from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans as proto_encode_spans,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest as PB2ExportLogsServiceRequest,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest as PB2ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest as PB2ExportTraceServiceRequest,
)
from opentelemetry.sdk.metrics import Exemplar
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event, SpanContext
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import Link

from tests import (
    BASE_TIME,
    PARENT_SPAN_ID,
    SPAN_ID,
    TIME,
    TRACE_ID,
    make_exponential_histogram,
    make_gauge,
    make_histogram,
    make_log,
    make_log_context,
    make_metrics_data,
    make_span,
    make_sum,
)

_HEX_ID_KEYS = frozenset({"traceId", "spanId", "parentSpanId"})


def _normalize_otlp_json(data: Any) -> Any:
    """Convert proto3 standard JSON (base64 IDs) to OTLP JSON (hex IDs)."""
    if isinstance(data, list):
        return [_normalize_otlp_json(item) for item in data]
    if isinstance(data, dict):
        return {
            key: (
                base64.b64decode(value).hex()
                if key in _HEX_ID_KEYS and isinstance(value, str)
                else _normalize_otlp_json(value)
            )
            for key, value in data.items()
        }
    return data


def _denormalize_otlp_json(data: Any) -> Any:
    """Convert OTLP JSON (hex IDs) back to proto3 standard JSON (base64 IDs)."""
    if isinstance(data, list):
        return [_denormalize_otlp_json(item) for item in data]
    if isinstance(data, dict):
        return {
            key: (
                base64.b64encode(bytes.fromhex(value)).decode("utf-8")
                if key in _HEX_ID_KEYS and isinstance(value, str)
                else _denormalize_otlp_json(value)
            )
            for key, value in data.items()
        }
    return data


def _make_spans():
    parent_ctx = SpanContext(TRACE_ID, PARENT_SPAN_ID, is_remote=True)
    link_ctx = SpanContext(TRACE_ID, 0x2222222222222222, is_remote=False)

    span1 = make_span(
        name="span-with-everything",
        parent=parent_ctx,
        events=(
            Event(
                name="event1",
                timestamp=BASE_TIME + 10 * 10**6,
                attributes={"event_key": "event_val", "event_int": 42},
            ),
        ),
        links=(Link(context=link_ctx, attributes={"link_bool": True}),),
        resource=Resource(
            {"service.name": "test-service"},
            schema_url="resource_schema",
        ),
        instrumentation_scope=InstrumentationScope(
            name="test_lib",
            version="1.0.0",
            schema_url="scope_schema",
        ),
    )

    span2 = make_span(
        name="bare-span",
        span_id=0xBBBBBBBBBBBBBBBB,
        parent=None,
        resource=Resource({"service.name": "test-service"}),
        start_time=BASE_TIME + 100 * 10**6,
        end_time=BASE_TIME + 200 * 10**6,
    )

    return [span1, span2]


def _make_test_metrics_data():
    return make_metrics_data(
        [
            make_sum(
                name="counter",
                value=100,
                attributes={"method": "GET"},
                description="a counter",
                unit="1",
            ),
            make_gauge(
                name="gauge_float",
                value=52.5,
                attributes={"host": "localhost"},
                description="a gauge",
                unit="ms",
            ),
            make_histogram(
                name="histogram",
                attributes={"path": "/api"},
                count=10,
                sum_value=500.0,
                bucket_counts=[2, 5, 3],
                explicit_bounds=[100.0, 250.0],
                min_value=10.0,
                max_value=450.0,
                exemplars=[
                    Exemplar(
                        {"sampled": "true"},
                        298.0,
                        TIME,
                        SPAN_ID,
                        TRACE_ID,
                    ),
                ],
                description="a histogram",
                unit="ms",
            ),
            make_exponential_histogram(
                name="exp_histogram",
                attributes={},
                count=8,
                sum_value=80.0,
                scale=2,
                zero_count=1,
                min_value=1.0,
                max_value=30.0,
                description="exponential",
            ),
        ],
        resource_attrs={"service.name": "metrics-svc"},
        resource_schema_url="resource_schema",
        scope_name="metrics_lib",
        scope_version="2.0",
        scope_schema_url="scope_schema",
    )


def _make_logs():
    ctx = make_log_context()
    return [
        make_log(
            body="something went wrong",
            severity_text="ERROR",
            severity_number=SeverityNumber.ERROR,
            attributes={"error.code": 500, "path": "/api"},
            context=ctx,
            resource=Resource({"service.name": "log-svc"}, "resource_schema"),
            instrumentation_scope=InstrumentationScope(
                "log_lib", "1.0", "scope_schema"
            ),
        ),
        make_log(
            body="healthy",
            timestamp=TIME + 2000,
            observed_timestamp=TIME + 3000,
            resource=Resource({"service.name": "log-svc"}),
            instrumentation_scope=InstrumentationScope("log_lib", "1.0"),
        ),
    ]


class TestProtoJsonDictCompatibility(unittest.TestCase):
    """Compare .to_dict() from JSON encoder with MessageToDict from proto
    encoder (after normalizing IDs)."""

    def test_trace_dict_compatibility(self):
        spans = _make_spans()
        json_dict = json_encode_spans(spans).to_dict()
        proto_dict = MessageToDict(
            proto_encode_spans(spans),
            preserving_proto_field_name=False,
            use_integers_for_enums=True,
        )
        self.assertEqual(json_dict, _normalize_otlp_json(proto_dict))

    def test_metrics_dict_compatibility(self):
        data = _make_test_metrics_data()
        json_dict = json_encode_metrics(data).to_dict()
        proto_dict = MessageToDict(
            proto_encode_metrics(data),
            preserving_proto_field_name=False,
            use_integers_for_enums=True,
        )
        self.assertEqual(json_dict, _normalize_otlp_json(proto_dict))

    def test_log_dict_compatibility(self):
        logs = _make_logs()
        json_dict = json_encode_logs(logs).to_dict()
        proto_dict = MessageToDict(
            proto_encode_logs(logs),
            preserving_proto_field_name=False,
            use_integers_for_enums=True,
        )
        self.assertEqual(json_dict, _normalize_otlp_json(proto_dict))


class TestProtoJsonParseCompatibility(unittest.TestCase):
    """Encode SDK objects to dict via JSON encoder, denormalize (hex→base64
    IDs), parse into protobuf via ParseDict, compare with proto encoder."""

    def test_trace_parse_compatibility(self):
        spans = _make_spans()
        json_dict = json_encode_spans(spans).to_dict()
        proto_expected = proto_encode_spans(spans)

        denormalized = _denormalize_otlp_json(json_dict)
        proto_parsed = ParseDict(denormalized, PB2ExportTraceServiceRequest())
        self.assertEqual(proto_parsed, proto_expected)

    def test_metrics_parse_compatibility(self):
        data = _make_test_metrics_data()
        json_dict = json_encode_metrics(data).to_dict()
        proto_expected = proto_encode_metrics(data)

        denormalized = _denormalize_otlp_json(json_dict)
        proto_parsed = ParseDict(
            denormalized, PB2ExportMetricsServiceRequest()
        )
        self.assertEqual(proto_parsed, proto_expected)

    def test_log_parse_compatibility(self):
        logs = _make_logs()
        json_dict = json_encode_logs(logs).to_dict()
        proto_expected = proto_encode_logs(logs)

        denormalized = _denormalize_otlp_json(json_dict)
        proto_parsed = ParseDict(denormalized, PB2ExportLogsServiceRequest())
        self.assertEqual(proto_parsed, proto_expected)
