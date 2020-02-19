# Copyright 2019, OpenTelemetry Authors
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
from opencensus.proto.trace.v1 import trace_pb2

from opentelemetry import trace as trace_api
from opentelemetry.ext.otcollector.trace_exporter import CollectorSpanExporter
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace import TraceOptions


class TestCollectorSpanExporter(unittest.TestCase):
    def test_constructor(self):
        mock_get_node = mock.Mock()
        patch = mock.patch(
            "opentelemetry.ext.otcollector.util.get_node",
            side_effect=mock_get_node,
        )
        service_name = "testServiceName"
        host_name = "testHostName"
        client = grpc.insecure_channel("")
        endpoint = "testEndpoint"
        with patch:
            exporter = CollectorSpanExporter(
                service_name=service_name,
                host_name=host_name,
                endpoint=endpoint,
                client=client,
            )

        self.assertIs(exporter.client, client)
        self.assertEqual(exporter.endpoint, endpoint)
        mock_get_node.assert_called_with(service_name, host_name)

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    def test_export(self):
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        parent_id = 0x1111111111111111
        other_id = 0x2222222222222222
        start_time = 683647322 * 10 ** 9  # in ns

        duration = 50 * 10 ** 6
        end_time = start_time + duration
        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            trace_options=TraceOptions(TraceOptions.SAMPLED),
            trace_state=trace_api.TraceState({"testKey": "testValue"}),
        )
        parent_context = trace_api.SpanContext(trace_id, parent_id)
        other_context = trace_api.SpanContext(trace_id, other_id)
        event_attributes = {
            "annotation_bool": True,
            "annotation_string": "annotation_test",
            "key_float": 0.3,
        }
        event_timestamp = start_time + 50 * 10 ** 6
        event = trace_api.Event(
            name="event0",
            timestamp=event_timestamp,
            attributes=event_attributes,
        )
        link_attributes = {"key_bool": True}
        link = trace_api.Link(
            context=other_context, attributes=link_attributes
        )
        otel_spans = [
            trace.Span(
                name="test1",
                context=span_context,
                parent=parent_context,
                events=(event,),
                links=(link,),
                kind=trace_api.SpanKind.CLIENT,
            )
        ]
        otel_spans[0].start(start_time=start_time)
        otel_spans[0].set_attribute("key_bool", False)
        otel_spans[0].set_attribute("key_string", "hello_world")
        otel_spans[0].set_attribute("key_float", 111.22)
        otel_spans[0].set_attribute("key_int", 333)
        otel_spans[0].set_status(
            trace_api.Status(
                trace_api.status.StatusCanonicalCode.INTERNAL,
                "test description",
            )
        )
        otel_spans[0].end(end_time=end_time)

        mock_client = mock.MagicMock()
        mock_export = mock.MagicMock()
        mock_client.Export = mock_export
        host_name = "testHostName"
        collector_exporter = CollectorSpanExporter(
            client=mock_client, host_name=host_name
        )

        result_status = collector_exporter.export(otel_spans)
        self.assertEqual(SpanExportResult.SUCCESS, result_status)

        export_arg = mock_export.call_args[0]
        service_request = next(export_arg[0])
        output_spans = getattr(service_request, "spans")
        output_node = getattr(service_request, "node")
        self.assertTrue(len(output_spans) == 1)
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
            output_spans[0].start_time.seconds, int(start_time / 1000000000)
        )
        self.assertEqual(
            output_spans[0].end_time.seconds, int(end_time / 1000000000)
        )
        self.assertEqual(output_spans[0].kind, trace_api.SpanKind.CLIENT.value)

        self.assertEqual(
            output_spans[0].parent_span_id, b"\x11\x11\x11\x11\x11\x11\x11\x11"
        )
        self.assertEqual(
            output_spans[0].status.code,
            trace_api.status.StatusCanonicalCode.INTERNAL.value,
        )
        self.assertEqual(output_spans[0].status.message, "test description")
        self.assertTrue(len(output_spans[0].tracestate.entries) == 1)
        self.assertEqual(output_spans[0].tracestate.entries[0].key, "testKey")
        self.assertEqual(
            output_spans[0].tracestate.entries[0].value, "testValue"
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
        self.assertEqual(output_spans[0].links.link[0].span_id, b'""""""""')
        self.assertEqual(
            output_spans[0].links.link[0].type,
            trace_pb2.Span.Link.Type.TYPE_UNSPECIFIED,
        )
        self.assertEqual(
            output_spans[0]
            .links.link[0]
            .attributes.attribute_map["key_bool"]
            .bool_value,
            True,
        )

        self.assertIsNotNone(getattr(output_node, "library_info"))
        self.assertIsNotNone(getattr(output_node, "service_info"))
        output_identifier = getattr(output_node, "identifier")
        self.assertEqual(
            getattr(output_identifier, "host_name"), "testHostName"
        )
