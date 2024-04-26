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

# pylint: disable=protected-access

import unittest
from typing import List, Tuple

from opentelemetry.exporter.otlp.proto.common._internal import (
    _encode_span_id,
    _encode_trace_id,
)
from opentelemetry.exporter.otlp.proto.common._internal.trace_encoder import (
    _SPAN_KIND_MAP,
    _encode_status,
)
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest as PB2ExportTraceServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue as PB2AnyValue
from opentelemetry.proto.common.v1.common_pb2 import (
    InstrumentationScope as PB2InstrumentationScope,
)
from opentelemetry.proto.common.v1.common_pb2 import KeyValue as PB2KeyValue
from opentelemetry.proto.resource.v1.resource_pb2 import (
    Resource as PB2Resource,
)
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans as PB2ResourceSpans,
)
from opentelemetry.proto.trace.v1.trace_pb2 import ScopeSpans as PB2ScopeSpans
from opentelemetry.proto.trace.v1.trace_pb2 import Span as PB2SPan
from opentelemetry.proto.trace.v1.trace_pb2 import Status as PB2Status
from opentelemetry.sdk.trace import Event as SDKEvent
from opentelemetry.sdk.trace import Resource as SDKResource
from opentelemetry.sdk.trace import SpanContext as SDKSpanContext
from opentelemetry.sdk.trace import _Span as SDKSpan
from opentelemetry.sdk.util.instrumentation import (
    InstrumentationScope as SDKInstrumentationScope,
)
from opentelemetry.trace import Link as SDKLink
from opentelemetry.trace import SpanKind as SDKSpanKind
from opentelemetry.trace import TraceFlags as SDKTraceFlags
from opentelemetry.trace.status import Status as SDKStatus
from opentelemetry.trace.status import StatusCode as SDKStatusCode


class TestOTLPTraceEncoder(unittest.TestCase):
    def test_encode_spans(self):
        otel_spans, expected_encoding = self.get_exhaustive_test_spans()
        self.assertEqual(encode_spans(otel_spans), expected_encoding)

    @staticmethod
    def get_exhaustive_otel_span_list() -> List[SDKSpan]:
        trace_id = 0x3E0C63257DE34C926F9EFCD03927272E

        base_time = 683647322 * 10**9  # in ns
        start_times = (
            base_time,
            base_time + 150 * 10**6,
            base_time + 300 * 10**6,
            base_time + 400 * 10**6,
        )
        end_times = (
            start_times[0] + (50 * 10**6),
            start_times[1] + (100 * 10**6),
            start_times[2] + (200 * 10**6),
            start_times[3] + (300 * 10**6),
        )

        parent_span_context = SDKSpanContext(
            trace_id, 0x1111111111111111, is_remote=True
        )

        other_context = SDKSpanContext(
            trace_id, 0x2222222222222222, is_remote=False
        )

        span1 = SDKSpan(
            name="test-span-1",
            context=SDKSpanContext(
                trace_id,
                0x34BF92DEEFC58C92,
                is_remote=False,
                trace_flags=SDKTraceFlags(SDKTraceFlags.SAMPLED),
            ),
            parent=parent_span_context,
            events=(
                SDKEvent(
                    name="event0",
                    timestamp=base_time + 50 * 10**6,
                    attributes={
                        "annotation_bool": True,
                        "annotation_string": "annotation_test",
                        "key_float": 0.3,
                    },
                ),
            ),
            links=(
                SDKLink(context=other_context, attributes={"key_bool": True}),
            ),
            resource=SDKResource({}, "resource_schema_url"),
        )
        span1.start(start_time=start_times[0])
        span1.set_attribute("key_bool", False)
        span1.set_attribute("key_string", "hello_world")
        span1.set_attribute("key_float", 111.22)
        span1.set_status(SDKStatus(SDKStatusCode.ERROR, "Example description"))
        span1.end(end_time=end_times[0])

        span2 = SDKSpan(
            name="test-span-2",
            context=parent_span_context,
            parent=None,
            resource=SDKResource(attributes={"key_resource": "some_resource"}),
        )
        span2.start(start_time=start_times[1])
        span2.end(end_time=end_times[1])

        span3 = SDKSpan(
            name="test-span-3",
            context=other_context,
            parent=None,
            resource=SDKResource(attributes={"key_resource": "some_resource"}),
        )
        span3.start(start_time=start_times[2])
        span3.set_attribute("key_string", "hello_world")
        span3.end(end_time=end_times[2])

        span4 = SDKSpan(
            name="test-span-4",
            context=other_context,
            parent=None,
            resource=SDKResource({}, "resource_schema_url"),
            instrumentation_scope=SDKInstrumentationScope(
                name="name", version="version"
            ),
        )
        span4.start(start_time=start_times[3])
        span4.end(end_time=end_times[3])

        return [span1, span2, span3, span4]

    def get_exhaustive_test_spans(
        self,
    ) -> Tuple[List[SDKSpan], PB2ExportTraceServiceRequest]:
        otel_spans = self.get_exhaustive_otel_span_list()
        trace_id = _encode_trace_id(otel_spans[0].context.trace_id)
        span_kind = _SPAN_KIND_MAP[SDKSpanKind.INTERNAL]

        pb2_service_request = PB2ExportTraceServiceRequest(
            resource_spans=[
                PB2ResourceSpans(
                    schema_url="resource_schema_url",
                    resource=PB2Resource(),
                    scope_spans=[
                        PB2ScopeSpans(
                            scope=PB2InstrumentationScope(),
                            spans=[
                                PB2SPan(
                                    trace_id=trace_id,
                                    span_id=_encode_span_id(
                                        otel_spans[0].context.span_id
                                    ),
                                    trace_state=None,
                                    parent_span_id=_encode_span_id(
                                        otel_spans[0].parent.span_id
                                    ),
                                    name=otel_spans[0].name,
                                    kind=span_kind,
                                    start_time_unix_nano=otel_spans[
                                        0
                                    ].start_time,
                                    end_time_unix_nano=otel_spans[0].end_time,
                                    attributes=[
                                        PB2KeyValue(
                                            key="key_bool",
                                            value=PB2AnyValue(
                                                bool_value=False
                                            ),
                                        ),
                                        PB2KeyValue(
                                            key="key_string",
                                            value=PB2AnyValue(
                                                string_value="hello_world"
                                            ),
                                        ),
                                        PB2KeyValue(
                                            key="key_float",
                                            value=PB2AnyValue(
                                                double_value=111.22
                                            ),
                                        ),
                                    ],
                                    events=[
                                        PB2SPan.Event(
                                            name="event0",
                                            time_unix_nano=otel_spans[0]
                                            .events[0]
                                            .timestamp,
                                            attributes=[
                                                PB2KeyValue(
                                                    key="annotation_bool",
                                                    value=PB2AnyValue(
                                                        bool_value=True
                                                    ),
                                                ),
                                                PB2KeyValue(
                                                    key="annotation_string",
                                                    value=PB2AnyValue(
                                                        string_value="annotation_test"
                                                    ),
                                                ),
                                                PB2KeyValue(
                                                    key="key_float",
                                                    value=PB2AnyValue(
                                                        double_value=0.3
                                                    ),
                                                ),
                                            ],
                                        )
                                    ],
                                    links=[
                                        PB2SPan.Link(
                                            trace_id=_encode_trace_id(
                                                otel_spans[0]
                                                .links[0]
                                                .context.trace_id
                                            ),
                                            span_id=_encode_span_id(
                                                otel_spans[0]
                                                .links[0]
                                                .context.span_id
                                            ),
                                            attributes=[
                                                PB2KeyValue(
                                                    key="key_bool",
                                                    value=PB2AnyValue(
                                                        bool_value=True
                                                    ),
                                                ),
                                            ],
                                            flags=0x100,
                                        )
                                    ],
                                    status=PB2Status(
                                        code=SDKStatusCode.ERROR.value,
                                        message="Example description",
                                    ),
                                    flags=0x300,
                                )
                            ],
                        ),
                        PB2ScopeSpans(
                            scope=PB2InstrumentationScope(
                                name="name",
                                version="version",
                            ),
                            spans=[
                                PB2SPan(
                                    trace_id=trace_id,
                                    span_id=_encode_span_id(
                                        otel_spans[3].context.span_id
                                    ),
                                    trace_state=None,
                                    parent_span_id=None,
                                    name=otel_spans[3].name,
                                    kind=span_kind,
                                    start_time_unix_nano=otel_spans[
                                        3
                                    ].start_time,
                                    end_time_unix_nano=otel_spans[3].end_time,
                                    attributes=None,
                                    events=None,
                                    links=None,
                                    status={},
                                    flags=0x100,
                                )
                            ],
                        ),
                    ],
                ),
                PB2ResourceSpans(
                    resource=PB2Resource(
                        attributes=[
                            PB2KeyValue(
                                key="key_resource",
                                value=PB2AnyValue(
                                    string_value="some_resource"
                                ),
                            )
                        ]
                    ),
                    scope_spans=[
                        PB2ScopeSpans(
                            scope=PB2InstrumentationScope(),
                            spans=[
                                PB2SPan(
                                    trace_id=trace_id,
                                    span_id=_encode_span_id(
                                        otel_spans[1].context.span_id
                                    ),
                                    trace_state=None,
                                    parent_span_id=None,
                                    name=otel_spans[1].name,
                                    kind=span_kind,
                                    start_time_unix_nano=otel_spans[
                                        1
                                    ].start_time,
                                    end_time_unix_nano=otel_spans[1].end_time,
                                    attributes=None,
                                    events=None,
                                    links=None,
                                    status={},
                                    flags=0x100,
                                ),
                                PB2SPan(
                                    trace_id=trace_id,
                                    span_id=_encode_span_id(
                                        otel_spans[2].context.span_id
                                    ),
                                    trace_state=None,
                                    parent_span_id=None,
                                    name=otel_spans[2].name,
                                    kind=span_kind,
                                    start_time_unix_nano=otel_spans[
                                        2
                                    ].start_time,
                                    end_time_unix_nano=otel_spans[2].end_time,
                                    attributes=[
                                        PB2KeyValue(
                                            key="key_string",
                                            value=PB2AnyValue(
                                                string_value="hello_world"
                                            ),
                                        ),
                                    ],
                                    events=None,
                                    links=None,
                                    status={},
                                    flags=0x100,
                                ),
                            ],
                        )
                    ],
                ),
            ]
        )

        return otel_spans, pb2_service_request

    def test_encode_status_code_translations(self):
        self.assertEqual(
            _encode_status(SDKStatus(status_code=SDKStatusCode.UNSET)),
            PB2Status(
                code=SDKStatusCode.UNSET.value,
            ),
        )

        self.assertEqual(
            _encode_status(SDKStatus(status_code=SDKStatusCode.OK)),
            PB2Status(
                code=SDKStatusCode.OK.value,
            ),
        )

        self.assertEqual(
            _encode_status(SDKStatus(status_code=SDKStatusCode.ERROR)),
            PB2Status(
                code=SDKStatusCode.ERROR.value,
            ),
        )
