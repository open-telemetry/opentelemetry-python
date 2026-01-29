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

import json
import unittest
from typing import List

from opentelemetry.exporter.otlp.json.common._internal.trace_encoder import (
    _encode_status,
    _get_span_kind_value,
)
from opentelemetry.exporter.otlp.json.common.encoding import IdEncoding
from opentelemetry.exporter.otlp.json.common.trace_encoder import encode_spans
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


class TestTraceEncoder(unittest.TestCase):
    def test_encode_spans(self):
        # Create test spans
        otel_spans = self.get_test_span_list()

        # Encode spans to JSON with hex ids
        json_spans = encode_spans(otel_spans, IdEncoding.HEX)

        # Check ids in hex format
        self.assertEqual(
            json_spans["resourceSpans"][0]["scopeSpans"][0]["spans"][0][
                "spanId"
            ],
            "34bf92deefc58c92",
        )

        # Encode spans to JSON
        json_spans = encode_spans(otel_spans)

        # Verify the structure is correct
        self.assertIn("resourceSpans", json_spans)
        self.assertEqual(len(json_spans["resourceSpans"]), 3)

        # Verify the content of the first resource span
        resource_span = json_spans["resourceSpans"][0]
        self.assertIn("resource", resource_span)
        self.assertIn("scopeSpans", resource_span)

        # Convert to JSON and back to ensure it's JSON-serializable
        json_str = json.dumps(json_spans)
        parsed_json = json.loads(json_str)
        self.assertEqual(len(parsed_json["resourceSpans"]), 3)

    def test_encode_status(self):
        # Test encoding of status codes
        status = SDKStatus(
            status_code=SDKStatusCode.ERROR, description="Error description"
        )
        json_status = _encode_status(status)

        # In ProtoJSON format, status code is a string
        self.assertEqual(json_status["code"], "STATUS_CODE_ERROR")
        self.assertEqual(json_status["message"], "Error description")

        # Test with empty description
        status = SDKStatus(status_code=SDKStatusCode.OK)
        json_status = _encode_status(status)

        # In ProtoJSON format, status code is a string
        self.assertEqual(json_status["code"], "STATUS_CODE_OK")

        # Test with UNSET status
        status = SDKStatus(status_code=SDKStatusCode.UNSET)
        json_status = _encode_status(status)

        # In ProtoJSON format, status code is a string
        self.assertEqual(json_status["code"], "STATUS_CODE_UNSET")

    def test_span_kind_mapping(self):
        # Verify all span kinds are mapped correctly to ProtoJSON string values
        self.assertEqual(
            _get_span_kind_value(SDKSpanKind.INTERNAL), "SPAN_KIND_INTERNAL"
        )
        self.assertEqual(
            _get_span_kind_value(SDKSpanKind.SERVER), "SPAN_KIND_SERVER"
        )
        self.assertEqual(
            _get_span_kind_value(SDKSpanKind.CLIENT), "SPAN_KIND_CLIENT"
        )
        self.assertEqual(
            _get_span_kind_value(SDKSpanKind.PRODUCER), "SPAN_KIND_PRODUCER"
        )
        self.assertEqual(
            _get_span_kind_value(SDKSpanKind.CONSUMER), "SPAN_KIND_CONSUMER"
        )

    @staticmethod
    def get_test_span_list() -> List[SDKSpan]:
        """Create a test list of spans for encoding tests."""
        trace_id = 0x3E0C63257DE34C926F9EFCD03927272E

        base_time = 683647322 * 10**9  # in ns
        start_times = (
            base_time,
            base_time + 150 * 10**6,
            base_time + 300 * 10**6,
            base_time + 400 * 10**6,
            base_time + 500 * 10**6,
            base_time + 600 * 10**6,
        )
        end_times = (
            start_times[0] + (50 * 10**6),
            start_times[1] + (100 * 10**6),
            start_times[2] + (200 * 10**6),
            start_times[3] + (300 * 10**6),
            start_times[4] + (400 * 10**6),
            start_times[5] + (500 * 10**6),
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

        span5 = SDKSpan(
            name="test-span-5",
            context=other_context,
            parent=None,
            resource=SDKResource(
                attributes={"key_resource": "another_resource"},
                schema_url="resource_schema_url",
            ),
            instrumentation_scope=SDKInstrumentationScope(
                name="scope_1_name",
                version="scope_1_version",
                schema_url="scope_1_schema_url",
            ),
        )
        span5.start(start_time=start_times[4])
        span5.end(end_time=end_times[4])

        span6 = SDKSpan(
            name="test-span-6",
            context=other_context,
            parent=None,
            resource=SDKResource(
                attributes={"key_resource": "another_resource"},
                schema_url="resource_schema_url",
            ),
            instrumentation_scope=SDKInstrumentationScope(
                name="scope_2_name",
                version="scope_2_version",
                schema_url="scope_2_schema_url",
                attributes={"one": "1", "two": 2},
            ),
        )
        span6.start(start_time=start_times[5])
        span6.end(end_time=end_times[5])

        return [span1, span2, span3, span4, span5, span6]
