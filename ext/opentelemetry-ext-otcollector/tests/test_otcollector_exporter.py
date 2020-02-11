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

import grpc
import json
import unittest
from unittest import mock

from google.protobuf.timestamp_pb2 import Timestamp

from opencensus.proto.agent.common.v1 import common_pb2
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

    def test_export(self):
        span_names = ("test1", "test2", "test3")
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        parent_id = 0x1111111111111111
        other_id = 0x2222222222222222

        base_time = 683647322 * 10 ** 9  # in ns
        start_times = (
            base_time,
            base_time + 150 * 10 ** 6,
            base_time + 300 * 10 ** 6,
        )
        durations = (50 * 10 ** 6, 100 * 10 ** 6, 200 * 10 ** 6)
        end_times = (
            start_times[0] + durations[0],
            start_times[1] + durations[1],
            start_times[2] + durations[2],
        )

        span_context = trace_api.SpanContext(
            trace_id, span_id, trace_options=TraceOptions(TraceOptions.SAMPLED)
        )
        parent_context = trace_api.SpanContext(trace_id, parent_id)
        other_context = trace_api.SpanContext(trace_id, other_id)

        event_attributes = {
            "annotation_bool": True,
            "annotation_string": "annotation_test",
            "key_float": 0.3,
        }

        event_timestamp = base_time + 50 * 10 ** 6
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
                name=span_names[0],
                context=span_context,
                parent=parent_context,
                events=(event,),
                links=(link,),
                kind=trace_api.SpanKind.CLIENT,
            ),
            trace.Span(
                name=span_names[1], context=parent_context, parent=None
            ),
            trace.Span(name=span_names[2], context=other_context, parent=None),
        ]

        otel_spans[0].start_time = start_times[0]
        otel_spans[0].set_attribute("key_bool", False)
        otel_spans[0].set_attribute("key_string", "hello_world")
        otel_spans[0].set_attribute("key_float", 111.22)
        otel_spans[0].set_status(
            trace_api.Status(
                trace_api.status.StatusCanonicalCode.INTERNAL,
                "test description",
            )
        )
        otel_spans[0].end_time = end_times[0]

        otel_spans[1].start_time = start_times[1]
        otel_spans[1].end_time = end_times[1]

        otel_spans[2].start_time = start_times[2]
        otel_spans[2].end_time = end_times[2]

        mock_client = mock.MagicMock()
        mock_export = mock.MagicMock()
        mock_client.Export = mock_export
        host_name = "testHostName"
        collector_exporter = CollectorSpanExporter(
            client=mock_client, host_name=host_name
        )

        result_status = collector_exporter.export(otel_spans)
        self.assertEqual(SpanExportResult.SUCCESS, result_status)

        node_arg = mock_export.call_args[0]
        output_spans = getattr(node_arg[0], "spans")
        output_node = getattr(node_arg[0], "node")
        self.assertEqual(
            output_spans[0].trace_id, b"n\x0cc%}\xe3L\x92o\x9e\xfc\xd09''."
        )
        self.assertEqual(
            output_spans[0].span_id, b"4\xbf\x92\xde\xef\xc5\x8c\x92"
        )
        self.assertEqual(
            output_spans[0].name,
            trace_pb2.TruncatableString(value=span_names[0]),
        )
        self.assertEqual(
            output_spans[0].start_time.seconds,
            int(start_times[0] / 1000000000),
        )
        self.assertEqual(
            output_spans[0].end_time.seconds, int(end_times[0] / 1000000000)
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

        self.assertIsNotNone(getattr(output_node, "library_info"))
        self.assertIsNotNone(getattr(output_node, "service_info"))
        output_identifier = getattr(output_node, "identifier")
        self.assertEqual(
            getattr(output_identifier, "host_name"), "testHostName"
        )
