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

import unittest
from unittest import mock

import grpc
from google.protobuf.timestamp_pb2 import (  # pylint: disable=no-name-in-module
    Timestamp,
)
from opencensus.proto.trace.v1 import trace_pb2

import opentelemetry.exporter.opencensus.util as utils
from opentelemetry import trace as trace_api
from opentelemetry.exporter.opencensus.trace_exporter import (
    OpenCensusSpanExporter,
    translate_to_collector,
)
from opentelemetry.sdk import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.test.globals_test import TraceGlobalsTest
from opentelemetry.trace import TraceFlags


# pylint: disable=no-member
class TestCollectorSpanExporter(TraceGlobalsTest, unittest.TestCase):
    def test_constructor(self):
        mock_get_node = mock.Mock()
        patch = mock.patch(
            "opentelemetry.exporter.opencensus.util.get_node",
            side_effect=mock_get_node,
        )
        trace_api.set_tracer_provider(
            TracerProvider(
                resource=Resource.create({SERVICE_NAME: "testServiceName"})
            )
        )

        host_name = "testHostName"
        client = grpc.insecure_channel("")
        endpoint = "testEndpoint"
        with patch:
            exporter = OpenCensusSpanExporter(
                host_name=host_name,
                endpoint=endpoint,
                client=client,
            )

        self.assertIs(exporter.client, client)
        self.assertEqual(exporter.endpoint, endpoint)
        mock_get_node.assert_called_with("testServiceName", host_name)

    def test_get_collector_span_kind(self):
        result = utils.get_collector_span_kind(trace_api.SpanKind.SERVER)
        self.assertIs(result, trace_pb2.Span.SpanKind.SERVER)
        result = utils.get_collector_span_kind(trace_api.SpanKind.CLIENT)
        self.assertIs(result, trace_pb2.Span.SpanKind.CLIENT)
        result = utils.get_collector_span_kind(trace_api.SpanKind.CONSUMER)
        self.assertIs(result, trace_pb2.Span.SpanKind.SPAN_KIND_UNSPECIFIED)
        result = utils.get_collector_span_kind(trace_api.SpanKind.PRODUCER)
        self.assertIs(result, trace_pb2.Span.SpanKind.SPAN_KIND_UNSPECIFIED)
        result = utils.get_collector_span_kind(trace_api.SpanKind.INTERNAL)
        self.assertIs(result, trace_pb2.Span.SpanKind.SPAN_KIND_UNSPECIFIED)

    def test_proto_timestamp_from_time_ns(self):
        result = utils.proto_timestamp_from_time_ns(12345)
        self.assertIsInstance(result, Timestamp)
        self.assertEqual(result.nanos, 12345)

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    def test_translate_to_collector(self):
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        parent_id = 0x1111111111111111
        base_time = 683647322 * 10**9  # in ns
        start_times = (
            base_time,
            base_time + 150 * 10**6,
            base_time + 300 * 10**6,
        )
        durations = (50 * 10**6, 100 * 10**6, 200 * 10**6)
        end_times = (
            start_times[0] + durations[0],
            start_times[1] + durations[1],
            start_times[2] + durations[2],
        )
        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state=trace_api.TraceState([("testkey", "testvalue")]),
        )
        parent_span_context = trace_api.SpanContext(
            trace_id, parent_id, is_remote=False
        )
        other_context = trace_api.SpanContext(
            trace_id, span_id, is_remote=False
        )
        event_attributes = {
            "annotation_bool": True,
            "annotation_string": "annotation_test",
            "key_float": 0.3,
        }
        event_timestamp = base_time + 50 * 10**6
        event = trace.Event(
            name="event0",
            timestamp=event_timestamp,
            attributes=event_attributes,
        )
        link_attributes = {"key_bool": True}
        link_1 = trace_api.Link(
            context=other_context, attributes=link_attributes
        )
        link_2 = trace_api.Link(
            context=parent_span_context, attributes=link_attributes
        )
        span_1 = trace._Span(
            name="test1",
            context=span_context,
            parent=parent_span_context,
            events=(event,),
            links=(link_1,),
            kind=trace_api.SpanKind.CLIENT,
        )
        span_2 = trace._Span(
            name="test2",
            context=parent_span_context,
            parent=None,
            kind=trace_api.SpanKind.SERVER,
        )
        span_3 = trace._Span(
            name="test3",
            context=other_context,
            links=(link_2,),
            parent=span_2.get_span_context(),
        )
        otel_spans = [span_1, span_2, span_3]
        otel_spans[0].start(start_time=start_times[0])
        otel_spans[0].set_attribute("key_bool", False)
        otel_spans[0].set_attribute("key_string", "hello_world")
        otel_spans[0].set_attribute("key_float", 111.22)
        otel_spans[0].set_attribute("key_int", 333)
        otel_spans[0].set_status(trace_api.Status(trace_api.StatusCode.OK))
        otel_spans[0].end(end_time=end_times[0])
        otel_spans[1].start(start_time=start_times[1])
        otel_spans[1].set_status(
            trace_api.Status(
                trace_api.StatusCode.ERROR,
                {"test", "val"},
            )
        )
        otel_spans[1].end(end_time=end_times[1])
        otel_spans[2].start(start_time=start_times[2])
        otel_spans[2].end(end_time=end_times[2])
        output_spans = translate_to_collector(otel_spans)

        self.assertEqual(len(output_spans), 3)
        self.assertEqual(
            output_spans[0].trace_id, b"n\x0cc%}\xe3L\x92o\x9e\xfc\xd09''."
        )
        self.assertEqual(
            output_spans[0].span_id, b"4\xbf\x92\xde\xef\xc5\x8c\x92"
        )
        self.assertEqual(
            output_spans[0].name, trace_pb2.TruncatableString(value="test1")
        )
        self.assertEqual(
            output_spans[1].name, trace_pb2.TruncatableString(value="test2")
        )
        self.assertEqual(
            output_spans[2].name, trace_pb2.TruncatableString(value="test3")
        )
        self.assertEqual(
            output_spans[0].start_time.seconds,
            int(start_times[0] / 1000000000),
        )
        self.assertEqual(
            output_spans[0].end_time.seconds, int(end_times[0] / 1000000000)
        )
        self.assertEqual(output_spans[0].kind, trace_api.SpanKind.CLIENT.value)
        self.assertEqual(output_spans[1].kind, trace_api.SpanKind.SERVER.value)

        self.assertEqual(
            output_spans[0].parent_span_id, b"\x11\x11\x11\x11\x11\x11\x11\x11"
        )
        self.assertEqual(
            output_spans[2].parent_span_id, b"\x11\x11\x11\x11\x11\x11\x11\x11"
        )
        self.assertEqual(
            output_spans[0].status.code,
            trace_api.StatusCode.OK.value,
        )
        self.assertEqual(len(output_spans[0].tracestate.entries), 1)
        self.assertEqual(output_spans[0].tracestate.entries[0].key, "testkey")
        self.assertEqual(
            output_spans[0].tracestate.entries[0].value, "testvalue"
        )

        self.assertEqual(
            output_spans[0].attributes.attribute_map["key_bool"].bool_value,
            False,
        )
        self.assertEqual(
            output_spans[0]
            .attributes.attribute_map["key_string"]
            .string_value.value,
            "hello_world",
        )
        self.assertEqual(
            output_spans[0].attributes.attribute_map["key_float"].double_value,
            111.22,
        )
        self.assertEqual(
            output_spans[0].attributes.attribute_map["key_int"].int_value, 333
        )

        self.assertEqual(
            output_spans[0].time_events.time_event[0].time.seconds, 683647322
        )
        self.assertEqual(
            output_spans[0]
            .time_events.time_event[0]
            .annotation.description.value,
            "event0",
        )
        self.assertEqual(
            output_spans[0]
            .time_events.time_event[0]
            .annotation.attributes.attribute_map["annotation_bool"]
            .bool_value,
            True,
        )
        self.assertEqual(
            output_spans[0]
            .time_events.time_event[0]
            .annotation.attributes.attribute_map["annotation_string"]
            .string_value.value,
            "annotation_test",
        )
        self.assertEqual(
            output_spans[0]
            .time_events.time_event[0]
            .annotation.attributes.attribute_map["key_float"]
            .double_value,
            0.3,
        )

        self.assertEqual(
            output_spans[0].links.link[0].trace_id,
            b"n\x0cc%}\xe3L\x92o\x9e\xfc\xd09''.",
        )
        self.assertEqual(
            output_spans[0].links.link[0].span_id,
            b"4\xbf\x92\xde\xef\xc5\x8c\x92",
        )
        self.assertEqual(
            output_spans[0].links.link[0].type,
            trace_pb2.Span.Link.Type.TYPE_UNSPECIFIED,
        )
        self.assertEqual(
            output_spans[1].status.code,
            trace_api.StatusCode.ERROR.value,
        )
        self.assertEqual(
            output_spans[2].links.link[0].type,
            trace_pb2.Span.Link.Type.PARENT_LINKED_SPAN,
        )
        self.assertEqual(
            output_spans[0]
            .links.link[0]
            .attributes.attribute_map["key_bool"]
            .bool_value,
            True,
        )

    def test_export(self):
        mock_client = mock.MagicMock()
        mock_export = mock.MagicMock()
        mock_client.Export = mock_export
        host_name = "testHostName"
        collector_exporter = OpenCensusSpanExporter(
            client=mock_client, host_name=host_name
        )

        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        otel_spans = [
            trace._Span(
                name="test1",
                context=span_context,
                kind=trace_api.SpanKind.CLIENT,
            )
        ]
        result_status = collector_exporter.export(otel_spans)
        self.assertEqual(SpanExportResult.SUCCESS, result_status)

        # pylint: disable=unsubscriptable-object
        export_arg = mock_export.call_args[0]
        service_request = next(export_arg[0])
        output_spans = getattr(service_request, "spans")
        output_node = getattr(service_request, "node")
        self.assertEqual(len(output_spans), 1)
        self.assertIsNotNone(getattr(output_node, "library_info"))
        self.assertIsNotNone(getattr(output_node, "service_info"))
        output_identifier = getattr(output_node, "identifier")
        self.assertEqual(
            getattr(output_identifier, "host_name"), "testHostName"
        )

    def test_export_service_name(self):
        trace_api.set_tracer_provider(
            TracerProvider(
                resource=Resource.create({SERVICE_NAME: "testServiceName"})
            )
        )
        mock_client = mock.MagicMock()
        mock_export = mock.MagicMock()
        mock_client.Export = mock_export
        host_name = "testHostName"
        collector_exporter = OpenCensusSpanExporter(
            client=mock_client, host_name=host_name
        )
        self.assertEqual(
            collector_exporter.node.service_info.name, "testServiceName"
        )

        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        resource = Resource.create({SERVICE_NAME: "test"})
        otel_spans = [
            trace._Span(
                name="test1",
                context=span_context,
                kind=trace_api.SpanKind.CLIENT,
                resource=resource,
            )
        ]

        result_status = collector_exporter.export(otel_spans)
        self.assertEqual(SpanExportResult.SUCCESS, result_status)
        self.assertEqual(collector_exporter.node.service_info.name, "test")
