# Copyright 2018, OpenCensus Authors
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

import opentelemetry.ext.jaeger as jaeger_exporter
from opentelemetry import trace as trace_api
from opentelemetry.ext.jaeger.gen.jaeger import jaeger
from opentelemetry.sdk import trace


class TestJaegerSpanExporter(unittest.TestCase):
    def test_constructor_default(self):
        service_name = "my_service"
        host_name = "localhost"
        thrift_port = None
        agent_port = 6831
        collector_endpoint = "/api/traces?format=jaeger.thrift"
        exporter = jaeger_exporter.JaegerSpanExporter()

        self.assertEqual(exporter.service_name, service_name)
        self.assertEqual(exporter.collector_host_name, None)
        self.assertEqual(exporter.agent_host_name, host_name)
        self.assertEqual(exporter.agent_port, agent_port)
        self.assertEqual(exporter.collector_port, thrift_port)
        self.assertEqual(exporter.collector_endpoint, collector_endpoint)
        self.assertEqual(exporter.username, None)
        self.assertEqual(exporter.password, None)
        self.assertTrue(exporter.collector is None)
        self.assertTrue(exporter.agent_client is not None)

    def test_constructor_explicit(self):
        service = "my-opentelemetry-jaeger"
        collector_host_name = "opentelemetry.io"
        collector_port = 15875
        collector_endpoint = "/myapi/traces?format=jaeger.thrift"

        agent_port = 14268
        agent_host_name = "opentelemetry.com"

        username = "username"
        password = "password"
        auth = (username, password)

        exporter = jaeger_exporter.JaegerSpanExporter(
            service_name=service,
            collector_host_name=collector_host_name,
            collector_port=collector_port,
            collector_endpoint=collector_endpoint,
            agent_host_name=agent_host_name,
            agent_port=agent_port,
            username=username,
            password=password,
        )
        self.assertEqual(exporter.service_name, service)
        self.assertEqual(exporter.agent_host_name, agent_host_name)
        self.assertEqual(exporter.agent_port, agent_port)
        self.assertEqual(exporter.collector_host_name, collector_host_name)
        self.assertEqual(exporter.collector_port, collector_port)
        self.assertTrue(exporter.collector is not None)
        self.assertEqual(exporter.collector.auth, auth)
        # property should not construct new object
        collector = exporter.collector
        self.assertEqual(exporter.collector, collector)
        # property should construct new object
        exporter._collector = None
        exporter.username = None
        exporter.password = None
        self.assertNotEqual(exporter.collector, collector)
        self.assertTrue(exporter.collector.auth is None)

    def test_translate_to_jaeger(self):
        self.maxDiff = None

        span_names = ("test1", "test2", "test3")
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        trace_id_high = 0x6E0C63257DE34C92
        trace_id_low = 0x6F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        parent_id = 0x1111111111111111
        other_id = 0x2222222222222222

        base_time = 683647322 * 1e9  # in ns
        start_times = (base_time, base_time + 150 * 1e6, base_time + 300 * 1e6)
        durations = (50 * 1e6, 100 * 1e6, 200 * 1e6)
        end_times = (
            start_times[0] + durations[0],
            start_times[1] + durations[1],
            start_times[2] + durations[2],
        )

        span_context = trace_api.SpanContext(trace_id, span_id)
        parent_context = trace_api.SpanContext(trace_id, parent_id)
        other_context = trace_api.SpanContext(trace_id, other_id)

        span_attributes = {
            "key_bool": False,
            "key_string": "hello_world",
            "key_float": 111.22,
        }

        event_attributes = {
            "annotation_bool": True,
            "annotation_string": "annotation_test",
            "key_float": 0.3,
        }

        event_timestamp = base_time + 50e6
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
                attributes=span_attributes,
                events=(event,),
                links=(link,),
            ),
            trace.Span(
                name=span_names[1], context=parent_context, parent=None
            ),
            trace.Span(name=span_names[2], context=other_context, parent=None),
        ]

        otel_spans[0].start_time = start_times[0]
        otel_spans[0].end_time = end_times[0]

        otel_spans[1].start_time = start_times[1]
        otel_spans[1].end_time = end_times[1]

        otel_spans[2].start_time = start_times[2]
        otel_spans[2].end_time = end_times[2]

        exporter = jaeger_exporter.JaegerSpanExporter()
        spans = exporter.translate_to_jaeger(otel_spans)

        expected_spans = [
            jaeger.Span(
                operationName=span_names[0],
                traceIdHigh=trace_id_high,
                traceIdLow=trace_id_low,
                spanId=span_id,
                parentSpanId=parent_id,
                startTime=start_times[0] / 1e3,
                duration=durations[0] / 1e3,
                flags=0,
                tags=[
                    jaeger.Tag(
                        key="key_bool", vType=jaeger.TagType.BOOL, vBool=False
                    ),
                    jaeger.Tag(
                        key="key_string",
                        vType=jaeger.TagType.STRING,
                        vStr="hello_world",
                    ),
                    jaeger.Tag(
                        key="key_float",
                        vType=jaeger.TagType.DOUBLE,
                        vDouble=111.22,
                    ),
                ],
                references=[
                    jaeger.SpanRef(
                        refType=jaeger.SpanRefType.FOLLOWS_FROM,
                        traceIdHigh=trace_id_high,
                        traceIdLow=trace_id_low,
                        spanId=other_id,
                    )
                ],
                logs=[
                    jaeger.Log(
                        timestamp=event_timestamp / 1e3,
                        fields=[
                            jaeger.Tag(
                                key="annotation_bool",
                                vType=jaeger.TagType.BOOL,
                                vBool=True,
                            ),
                            jaeger.Tag(
                                key="annotation_string",
                                vType=jaeger.TagType.STRING,
                                vStr="annotation_test",
                            ),
                            jaeger.Tag(
                                key="key_float",
                                vType=jaeger.TagType.DOUBLE,
                                vDouble=0.3,
                            ),
                            jaeger.Tag(
                                key="message",
                                vType=jaeger.TagType.STRING,
                                vStr="event0",
                            ),
                        ],
                    )
                ],
            ),
            jaeger.Span(
                operationName=span_names[1],
                traceIdHigh=trace_id_high,
                traceIdLow=trace_id_low,
                spanId=parent_id,
                parentSpanId=0,
                startTime=int(start_times[1] // 1e3),
                duration=int(durations[1] // 1e3),
                flags=0,
            ),
            jaeger.Span(
                operationName=span_names[2],
                traceIdHigh=trace_id_high,
                traceIdLow=trace_id_low,
                spanId=other_id,
                parentSpanId=0,
                startTime=int(start_times[2] // 1e3),
                duration=int(durations[2] // 1e3),
                flags=0,
            ),
        ]

        spans_json = [span.format_span_json() for span in spans]
        expected_spans_json = [
            span.format_span_json() for span in expected_spans
        ]
        span = spans_json[0]
        expected_span = expected_spans_json[0]

        try:
            listsEqual = self.assertCountEqual
        except AttributeError:
            listsEqual = self.assertItemsEqual

        log = span.get("logs")[0]
        expected_log = expected_span.get("logs")[0]
        self.assertEqual(log.get("timestamp"), expected_log.get("timestamp"))
        listsEqual(log.get("fields"), expected_log.get("fields"))
        listsEqual(span.get("tags"), expected_span.get("tags"))
        listsEqual(span.get("references"), expected_span.get("references"))
        self.assertEqual(
            span.get("traceIdHigh"), expected_span.get("traceIdHigh")
        )
        self.assertEqual(
            span.get("traceIdLow"), expected_span.get("traceIdLow")
        )
        self.assertEqual(span.get("spanId"), expected_span.get("spanId"))
        self.assertEqual(
            span.get("parentSpanId"), expected_span.get("parentSpanId")
        )
        self.assertEqual(
            span.get("operationName"), expected_span.get("operationName")
        )
        self.assertEqual(span.get("startTime"), expected_span.get("startTime"))
        self.assertEqual(span.get("duration"), expected_span.get("duration"))
        self.assertEqual(span.get("flags"), expected_span.get("flags"))

        self.assertEqual(spans_json[1], expected_spans_json[1])
        self.assertEqual(spans_json[2], expected_spans_json[2])
