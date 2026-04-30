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

# pylint: disable=protected-access,unsubscriptable-object

import json
import unittest

from opentelemetry.exporter.otlp.json.common._internal import (
    _encode_span_id,
    _encode_trace_id,
)
from opentelemetry.exporter.otlp.json.common._internal.trace_encoder import (
    _SPAN_KIND_MAP,
    _encode_context_span_id,
    _encode_events,
    _encode_links,
    _encode_status,
    _encode_trace_state,
    _span_flags,
)
from opentelemetry.exporter.otlp.json.common.trace_encoder import encode_spans
from opentelemetry.proto_json.collector.trace.v1.trace_service import (
    ExportTraceServiceRequest as JSONExportTraceServiceRequest,
)
from opentelemetry.proto_json.common.v1.common import AnyValue as JSONAnyValue
from opentelemetry.proto_json.trace.v1.trace import Span as JSONSpan
from opentelemetry.proto_json.trace.v1.trace import (
    SpanFlags as JSONSpanFlags,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event, SpanContext
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import Link, SpanKind
from opentelemetry.trace.span import TraceState
from opentelemetry.trace.status import Status, StatusCode
from tests import (
    BASE_TIME,
    PARENT_SPAN_ID,
    SPAN_ID,
    TRACE_ID,
    assert_proto_json_equal,
    make_span,
    make_span_unended,
)


def _get_span(result, rs_idx=0, ss_idx=0, s_idx=0):
    return result.resource_spans[rs_idx].scope_spans[ss_idx].spans[s_idx]


# pylint: disable=too-many-public-methods
class TestOTLPTraceEncoder(unittest.TestCase):
    def test_encode_single_span(self):
        span = make_span()
        result = encode_spans([span])

        self.assertEqual(len(result.resource_spans), 1)
        self.assertEqual(len(result.resource_spans[0].scope_spans), 1)
        self.assertEqual(len(result.resource_spans[0].scope_spans[0].spans), 1)

        encoded = _get_span(result)
        self.assertEqual(encoded.name, "test-span")
        self.assertEqual(encoded.kind, JSONSpan.SpanKind.SPAN_KIND_INTERNAL)
        self.assertEqual(encoded.start_time_unix_nano, BASE_TIME)
        self.assertEqual(encoded.end_time_unix_nano, BASE_TIME + 50 * 10**6)
        self.assertEqual(encoded.trace_id, _encode_trace_id(TRACE_ID))
        self.assertEqual(encoded.span_id, _encode_span_id(SPAN_ID))

    def test_encode_span_attributes(self):
        span = make_span()
        span._attributes = {"key_bool": False, "key_str": "hello"}
        result = encode_spans([span])
        encoded = _get_span(result)

        attr_dict = {kv.key: kv.value for kv in encoded.attributes}
        self.assertEqual(attr_dict["key_bool"], JSONAnyValue(bool_value=False))
        self.assertEqual(
            attr_dict["key_str"], JSONAnyValue(string_value="hello")
        )

    def test_encode_span_events(self):
        event = Event(
            name="my-event",
            timestamp=BASE_TIME + 10 * 10**6,
            attributes={"event_key": "event_val"},
        )
        span = make_span(events=(event,))
        result = encode_spans([span])
        encoded = _get_span(result)

        self.assertEqual(len(encoded.events), 1)
        self.assertEqual(encoded.events[0].name, "my-event")
        self.assertEqual(
            encoded.events[0].time_unix_nano, BASE_TIME + 10 * 10**6
        )
        self.assertEqual(encoded.events[0].attributes[0].key, "event_key")

    def test_encode_span_links(self):
        link_ctx = SpanContext(TRACE_ID, 0x2222222222222222, is_remote=False)
        link = Link(context=link_ctx, attributes={"link_key": True})
        span = make_span(links=(link,))
        result = encode_spans([span])
        encoded = _get_span(result)

        self.assertEqual(len(encoded.links), 1)
        self.assertEqual(encoded.links[0].trace_id, _encode_trace_id(TRACE_ID))
        self.assertEqual(
            encoded.links[0].span_id,
            _encode_span_id(0x2222222222222222),
        )
        self.assertEqual(encoded.links[0].attributes[0].key, "link_key")
        self.assertEqual(
            encoded.links[0].flags,
            int(JSONSpanFlags.SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK),
        )

    def test_encode_span_status(self):
        cases = [
            ("unset", StatusCode.UNSET, None, 0),
            ("ok", StatusCode.OK, None, 1),
            ("error", StatusCode.ERROR, "Something broke", 2),
        ]
        for name, code, description, expected_code in cases:
            with self.subTest(name=name):
                span = make_span_unended()
                span.set_status(Status(code, description))
                span.end(end_time=BASE_TIME + 50 * 10**6)

                result = encode_spans([span])
                encoded = _get_span(result)
                self.assertEqual(int(encoded.status.code), expected_code)
                if description:
                    self.assertEqual(encoded.status.message, description)

    def test_encode_span_parent(self):
        parent_ctx = SpanContext(TRACE_ID, PARENT_SPAN_ID, is_remote=True)
        span = make_span(parent=parent_ctx)
        result = encode_spans([span])
        encoded = _get_span(result)

        self.assertEqual(
            encoded.parent_span_id,
            _encode_span_id(PARENT_SPAN_ID),
        )
        self.assertEqual(
            encoded.flags,
            int(
                JSONSpanFlags.SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK
                | JSONSpanFlags.SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK
            ),
        )

    def test_encode_span_no_parent(self):
        span = make_span(parent=None)
        result = encode_spans([span])
        encoded = _get_span(result)

        self.assertIsNone(encoded.parent_span_id)
        self.assertEqual(
            encoded.flags,
            int(JSONSpanFlags.SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK),
        )

    def test_encode_span_grouping_by_resource(self):
        r1 = Resource({"svc": "svc1"})
        r2 = Resource({"svc": "svc2"})
        span1 = make_span(name="s1", resource=r1, span_id=0xAAAA)
        span2 = make_span(name="s2", resource=r2, span_id=0xBBBB)

        result = encode_spans([span1, span2])
        self.assertEqual(len(result.resource_spans), 2)

        groups = {}
        # pylint: disable-next=not-an-iterable
        for rs in result.resource_spans:
            svc_val = rs.resource.attributes[0].value.string_value
            span_names = [s.name for ss in rs.scope_spans for s in ss.spans]
            groups[svc_val] = span_names

        self.assertEqual(groups["svc1"], ["s1"])
        self.assertEqual(groups["svc2"], ["s2"])

    def test_encode_span_grouping_by_scope(self):
        resource = Resource({"svc": "test"})
        scope1 = InstrumentationScope(name="lib1", version="1.0")
        scope2 = InstrumentationScope(name="lib2", version="2.0")
        span1 = make_span(
            name="s1",
            resource=resource,
            instrumentation_scope=scope1,
            span_id=0xAAAA,
        )
        span2 = make_span(
            name="s2",
            resource=resource,
            instrumentation_scope=scope2,
            span_id=0xBBBB,
        )

        result = encode_spans([span1, span2])
        self.assertEqual(len(result.resource_spans), 1)
        scope_spans = result.resource_spans[0].scope_spans
        self.assertEqual(len(scope_spans), 2)

        groups = {
            ss.scope.name: [s.name for s in ss.spans] for ss in scope_spans
        }
        self.assertEqual(groups["lib1"], ["s1"])
        self.assertEqual(groups["lib2"], ["s2"])
        self.assertEqual(scope_spans[0].scope.version, "1.0")
        self.assertEqual(scope_spans[1].scope.version, "2.0")

    def test_encode_span_schema_urls(self):
        resource = Resource({"key": "val"}, schema_url="resource_schema")
        scope = InstrumentationScope(
            name="lib",
            version="1.0",
            schema_url="scope_schema",
        )
        span = make_span(resource=resource, instrumentation_scope=scope)
        result = encode_spans([span])

        self.assertEqual(
            result.resource_spans[0].schema_url, "resource_schema"
        )
        self.assertEqual(
            result.resource_spans[0].scope_spans[0].schema_url,
            "scope_schema",
        )

    def test_encode_span_scope_attributes(self):
        scope = InstrumentationScope(
            name="lib",
            version="1.0",
            attributes={"scope_key": "scope_val"},
        )
        span = make_span(instrumentation_scope=scope)
        result = encode_spans([span])

        encoded_scope = result.resource_spans[0].scope_spans[0].scope
        self.assertEqual(encoded_scope.name, "lib")
        self.assertEqual(encoded_scope.version, "1.0")
        self.assertEqual(len(encoded_scope.attributes), 1)
        self.assertEqual(encoded_scope.attributes[0].key, "scope_key")

    def test_span_kind_map(self):
        expected = [
            (SpanKind.INTERNAL, JSONSpan.SpanKind.SPAN_KIND_INTERNAL),
            (SpanKind.SERVER, JSONSpan.SpanKind.SPAN_KIND_SERVER),
            (SpanKind.CLIENT, JSONSpan.SpanKind.SPAN_KIND_CLIENT),
            (SpanKind.PRODUCER, JSONSpan.SpanKind.SPAN_KIND_PRODUCER),
            (SpanKind.CONSUMER, JSONSpan.SpanKind.SPAN_KIND_CONSUMER),
        ]
        for sdk_kind, json_kind in expected:
            with self.subTest(kind=sdk_kind.name):
                self.assertEqual(_SPAN_KIND_MAP[sdk_kind], json_kind)

    def test_span_flags(self):
        cases = [
            (
                "remote_parent",
                SpanContext(TRACE_ID, 0x1111, is_remote=True),
                int(
                    JSONSpanFlags.SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK
                    | JSONSpanFlags.SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK
                ),
            ),
            (
                "local_parent",
                SpanContext(TRACE_ID, 0x2222, is_remote=False),
                int(JSONSpanFlags.SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK),
            ),
            (
                "no_parent",
                None,
                int(JSONSpanFlags.SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK),
            ),
        ]
        for name, context, expected_flags in cases:
            with self.subTest(name=name):
                self.assertEqual(_span_flags(context), expected_flags)

    def test_encode_status_translations(self):
        cases = [
            ("unset", StatusCode.UNSET, None),
            ("ok", StatusCode.OK, None),
            ("error", StatusCode.ERROR, "desc"),
        ]
        for name, code, desc in cases:
            with self.subTest(name=name):
                result = _encode_status(Status(code, desc))
                self.assertEqual(
                    int(result.code),
                    code.value,
                )
                if desc:
                    self.assertEqual(result.message, desc)

    def test_encode_trace_state(self):
        ts = TraceState([("key1", "val1"), ("key2", "val2")])
        self.assertEqual(_encode_trace_state(ts), "key1=val1,key2=val2")

    def test_encode_trace_state_none(self):
        self.assertIsNone(_encode_trace_state(None))

    def test_encode_events_empty(self):
        self.assertEqual(_encode_events(()), [])
        self.assertEqual(_encode_events([]), [])

    def test_encode_links_empty(self):
        self.assertEqual(_encode_links(()), [])
        self.assertEqual(_encode_links([]), [])

    def test_encode_parent_id(self):
        ctx = SpanContext(TRACE_ID, 0xABCDEF1234567890, is_remote=True)
        self.assertEqual(
            _encode_context_span_id(ctx),
            _encode_span_id(0xABCDEF1234567890),
        )

    def test_encode_parent_id_none(self):
        self.assertIsNone(_encode_context_span_id(None))

    def test_encode_spans_to_dict(self):
        span = make_span()
        span.set_attribute("key", "value")
        result = encode_spans([span])
        result_dict = result.to_dict()

        self.assertIn("resourceSpans", result_dict)
        sp = result_dict["resourceSpans"][0]["scopeSpans"][0]["spans"][0]

        self.assertIsInstance(sp["traceId"], str)
        self.assertEqual(len(sp["traceId"]), 32)
        self.assertIsInstance(sp["spanId"], str)
        self.assertEqual(len(sp["spanId"]), 16)
        self.assertIsInstance(sp["startTimeUnixNano"], str)
        self.assertIsInstance(sp["endTimeUnixNano"], str)

    def test_encode_spans_json_roundtrip(self):
        parent_ctx = SpanContext(TRACE_ID, PARENT_SPAN_ID, is_remote=True)
        spans = [
            make_span(name="span1", parent=parent_ctx),
            make_span(
                name="span2",
                span_id=0xBBBB,
                resource=Resource({"r": "v"}),
                instrumentation_scope=InstrumentationScope(
                    "lib", "1.0", attributes={"sk": 1}
                ),
            ),
        ]
        result = encode_spans(spans)
        json_str = result.to_json()
        roundtripped = JSONExportTraceServiceRequest.from_dict(
            json.loads(json_str)
        )
        assert_proto_json_equal(self, result, roundtripped)
