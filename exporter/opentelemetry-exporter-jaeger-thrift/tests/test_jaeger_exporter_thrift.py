# Copyright 2018, OpenCensus Authors
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
from unittest.mock import patch

# pylint:disable=no-name-in-module
# pylint:disable=import-error
import opentelemetry.exporter.jaeger.thrift as jaeger_exporter
from opentelemetry import trace as trace_api
from opentelemetry.exporter.jaeger.thrift.gen.jaeger import ttypes as jaeger
from opentelemetry.exporter.jaeger.thrift.translate import (
    ThriftTranslator,
    Translate,
)
from opentelemetry.sdk import trace
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_JAEGER_AGENT_HOST,
    OTEL_EXPORTER_JAEGER_AGENT_PORT,
    OTEL_EXPORTER_JAEGER_ENDPOINT,
    OTEL_EXPORTER_JAEGER_PASSWORD,
    OTEL_EXPORTER_JAEGER_TIMEOUT,
    OTEL_EXPORTER_JAEGER_USER,
)
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.sdk.trace import Resource, TracerProvider
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo
from opentelemetry.test.spantestutil import (
    get_span_with_dropped_attributes_events_links,
)
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCode


def _translate_spans_with_dropped_attributes():
    span = get_span_with_dropped_attributes_events_links()
    translate = Translate([span])

    # pylint: disable=protected-access
    return translate._translate(ThriftTranslator(max_tag_value_length=5))


class TestJaegerExporter(unittest.TestCase):
    def setUp(self):
        # create and save span to be used in tests
        self.context = trace_api.SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000DEADBEF0,
            is_remote=False,
        )

        self._test_span = trace._Span(
            "test_span",
            context=self.context,
            # Use a fixed version because a longer/shorter version number
            # might break tests that care about packet size.
            resource=Resource.create({"telemetry.sdk.version": "0.0.0.dev0"}),
        )
        self._test_span.start(start_time=1)
        self._test_span.end(end_time=3)
        # pylint: disable=protected-access

    @patch("opentelemetry.exporter.jaeger.thrift.trace._TRACER_PROVIDER", None)
    def test_constructor_default(self):
        # pylint: disable=protected-access
        """Test the default values assigned by constructor."""
        service_name = "my-service-name"
        agent_host_name = "localhost"
        agent_port = 6831

        trace_api.set_tracer_provider(
            TracerProvider(
                resource=Resource.create({SERVICE_NAME: "my-service-name"})
            )
        )

        exporter = jaeger_exporter.JaegerExporter()
        self.assertEqual(exporter.service_name, service_name)
        self.assertEqual(exporter.agent_host_name, agent_host_name)
        self.assertEqual(exporter.agent_port, agent_port)
        self.assertEqual(exporter.collector_endpoint, None)
        self.assertEqual(exporter.username, None)
        self.assertEqual(exporter.password, None)
        self.assertTrue(exporter._collector_http_client is None)
        self.assertTrue(exporter._agent_client is not None)
        self.assertIsNone(exporter._max_tag_value_length)

    @patch("opentelemetry.exporter.jaeger.thrift.trace._TRACER_PROVIDER", None)
    def test_constructor_explicit(self):
        # pylint: disable=protected-access
        """Test the constructor passing all the options."""
        service = "my-opentelemetry-jaeger"
        collector_endpoint = "https://opentelemetry.io:15875"

        agent_port = 14268
        agent_host_name = "opentelemetry.io"

        username = "username"
        password = "password"
        auth = (username, password)
        trace_api.set_tracer_provider(
            TracerProvider(
                resource=Resource.create(
                    {SERVICE_NAME: "my-opentelemetry-jaeger"}
                )
            )
        )

        exporter = jaeger_exporter.JaegerExporter(
            agent_host_name=agent_host_name,
            agent_port=agent_port,
            collector_endpoint=collector_endpoint,
            username=username,
            password=password,
            max_tag_value_length=42,
        )
        self.assertEqual(exporter.service_name, service)
        self.assertEqual(exporter.agent_host_name, agent_host_name)
        self.assertEqual(exporter.agent_port, agent_port)
        self.assertTrue(exporter._collector_http_client is not None)
        self.assertEqual(exporter._collector_http_client.auth, auth)
        # property should not construct new object
        collector = exporter._collector_http_client
        self.assertEqual(exporter._collector_http_client, collector)
        # property should construct new object
        exporter._collector = None
        exporter.username = None
        exporter.password = None
        self.assertNotEqual(exporter._collector_http_client, collector)
        self.assertTrue(exporter._collector_http_client.auth is None)
        self.assertEqual(exporter._max_tag_value_length, 42)

    @patch("opentelemetry.exporter.jaeger.thrift.trace._TRACER_PROVIDER", None)
    def test_constructor_by_environment_variables(self):
        #  pylint: disable=protected-access
        """Test the constructor using Environment Variables."""
        service = "my-opentelemetry-jaeger"

        agent_host_name = "opentelemetry.io"
        agent_port = "6831"

        collector_endpoint = "https://opentelemetry.io:15875"

        username = "username"
        password = "password"
        auth = (username, password)

        environ_patcher = mock.patch.dict(
            "os.environ",
            {
                OTEL_EXPORTER_JAEGER_AGENT_HOST: agent_host_name,
                OTEL_EXPORTER_JAEGER_AGENT_PORT: agent_port,
                OTEL_EXPORTER_JAEGER_ENDPOINT: collector_endpoint,
                OTEL_EXPORTER_JAEGER_USER: username,
                OTEL_EXPORTER_JAEGER_PASSWORD: password,
                OTEL_EXPORTER_JAEGER_TIMEOUT: "20",
            },
        )

        trace_api.set_tracer_provider(
            TracerProvider(
                resource=Resource.create(
                    {SERVICE_NAME: "my-opentelemetry-jaeger"}
                )
            )
        )

        environ_patcher.start()
        exporter = jaeger_exporter.JaegerExporter()
        self.assertEqual(exporter.service_name, service)
        self.assertEqual(exporter.agent_host_name, agent_host_name)
        self.assertEqual(exporter.agent_port, int(agent_port))
        self.assertEqual(exporter._timeout, 20)
        self.assertTrue(exporter._collector_http_client is not None)
        self.assertEqual(exporter.collector_endpoint, collector_endpoint)
        self.assertEqual(exporter._collector_http_client.auth, auth)
        # property should not construct new object
        collector = exporter._collector_http_client
        self.assertEqual(exporter._collector_http_client, collector)
        # property should construct new object
        exporter._collector = None
        exporter.username = None
        exporter.password = None
        self.assertNotEqual(exporter._collector_http_client, collector)
        self.assertTrue(exporter._collector_http_client.auth is None)
        environ_patcher.stop()

    @patch("opentelemetry.exporter.jaeger.thrift.trace._TRACER_PROVIDER", None)
    def test_constructor_with_no_traceprovider_resource(self):

        """Test the constructor when there is no resource attached to trace_provider"""

        exporter = jaeger_exporter.JaegerExporter()

        self.assertEqual(exporter.service_name, "unknown_service")

    def test_nsec_to_usec_round(self):
        # pylint: disable=protected-access
        nsec_to_usec_round = jaeger_exporter.translate._nsec_to_usec_round

        self.assertEqual(nsec_to_usec_round(5000), 5)
        self.assertEqual(nsec_to_usec_round(5499), 5)
        self.assertEqual(nsec_to_usec_round(5500), 6)

    def test_all_otlp_span_kinds_are_mapped(self):
        for kind in SpanKind:
            self.assertIn(
                kind, jaeger_exporter.translate.OTLP_JAEGER_SPAN_KIND
            )

    # pylint: disable=too-many-locals
    def test_translate_to_jaeger(self):
        # pylint: disable=invalid-name
        self.maxDiff = None

        span_names = ("test1", "test2", "test3")
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        trace_id_high = 0x6E0C63257DE34C92
        trace_id_low = 0x6F9EFCD03927272E
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
            trace_id, span_id, is_remote=False
        )
        parent_span_context = trace_api.SpanContext(
            trace_id, parent_id, is_remote=False
        )
        other_context = trace_api.SpanContext(
            trace_id, other_id, is_remote=False
        )

        event_attributes = {
            "annotation_bool": True,
            "annotation_string": "annotation_test",
            "key_float": 0.3,
        }

        event_timestamp = base_time + 50 * 10 ** 6
        event = trace.Event(
            name="event0",
            timestamp=event_timestamp,
            attributes=event_attributes,
        )

        link_attributes = {"key_bool": True}

        link = trace_api.Link(
            context=other_context, attributes=link_attributes
        )

        default_tags = [
            jaeger.Tag(
                key="span.kind",
                vType=jaeger.TagType.STRING,
                vStr="internal",
            ),
        ]

        otel_spans = [
            trace._Span(
                name=span_names[0],
                context=span_context,
                parent=parent_span_context,
                events=(event,),
                links=(link,),
                kind=trace_api.SpanKind.CLIENT,
                resource=Resource(
                    attributes={"key_resource": "some_resource"}
                ),
            ),
            trace._Span(
                name=span_names[1],
                context=parent_span_context,
                parent=None,
                resource=Resource({}),
            ),
            trace._Span(
                name=span_names[2],
                context=other_context,
                parent=None,
                resource=Resource({}),
                instrumentation_info=InstrumentationInfo(
                    name="name", version="version"
                ),
            ),
        ]

        otel_spans[0].start(start_time=start_times[0])
        # added here to preserve order
        otel_spans[0].set_attribute("key_bool", False)
        otel_spans[0].set_attribute("key_string", "hello_world")
        otel_spans[0].set_attribute("key_float", 111.22)
        otel_spans[0].set_attribute("key_tuple", ("tuple_element",))
        otel_spans[0].set_status(
            Status(StatusCode.ERROR, "Example description")
        )
        otel_spans[0].end(end_time=end_times[0])

        otel_spans[1].start(start_time=start_times[1])
        otel_spans[1].end(end_time=end_times[1])

        otel_spans[2].start(start_time=start_times[2])
        otel_spans[2].set_status(Status(StatusCode.OK))
        otel_spans[2].end(end_time=end_times[2])

        translate = Translate(otel_spans)
        # pylint: disable=protected-access
        spans = translate._translate(ThriftTranslator())

        expected_spans = [
            jaeger.Span(
                operationName=span_names[0],
                traceIdHigh=trace_id_high,
                traceIdLow=trace_id_low,
                spanId=span_id,
                parentSpanId=parent_id,
                startTime=start_times[0] // 10 ** 3,
                duration=durations[0] // 10 ** 3,
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
                    jaeger.Tag(
                        key="key_tuple",
                        vType=jaeger.TagType.STRING,
                        vStr="('tuple_element',)",
                    ),
                    jaeger.Tag(
                        key="key_resource",
                        vType=jaeger.TagType.STRING,
                        vStr="some_resource",
                    ),
                    jaeger.Tag(
                        key="otel.status_code",
                        vType=jaeger.TagType.STRING,
                        vStr="ERROR",
                    ),
                    jaeger.Tag(
                        key="otel.status_description",
                        vType=jaeger.TagType.STRING,
                        vStr="Example description",
                    ),
                    jaeger.Tag(
                        key="span.kind",
                        vType=jaeger.TagType.STRING,
                        vStr="client",
                    ),
                    jaeger.Tag(
                        key="error", vType=jaeger.TagType.BOOL, vBool=True
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
                        timestamp=event_timestamp // 10 ** 3,
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
                startTime=start_times[1] // 10 ** 3,
                duration=durations[1] // 10 ** 3,
                flags=0,
                tags=default_tags,
            ),
            jaeger.Span(
                operationName=span_names[2],
                traceIdHigh=trace_id_high,
                traceIdLow=trace_id_low,
                spanId=other_id,
                parentSpanId=0,
                startTime=start_times[2] // 10 ** 3,
                duration=durations[2] // 10 ** 3,
                flags=0,
                tags=[
                    jaeger.Tag(
                        key="otel.status_code",
                        vType=jaeger.TagType.STRING,
                        vStr="OK",
                    ),
                    jaeger.Tag(
                        key="span.kind",
                        vType=jaeger.TagType.STRING,
                        vStr="internal",
                    ),
                    jaeger.Tag(
                        key=jaeger_exporter.translate.NAME_KEY,
                        vType=jaeger.TagType.STRING,
                        vStr="name",
                    ),
                    jaeger.Tag(
                        key=jaeger_exporter.translate.VERSION_KEY,
                        vType=jaeger.TagType.STRING,
                        vStr="version",
                    ),
                ],
            ),
        ]

        # events are complicated to compare because order of fields
        # (attributes) in otel is not important but in jeager it is
        self.assertCountEqual(
            spans[0].logs[0].fields, expected_spans[0].logs[0].fields
        )
        # get rid of fields to be able to compare the whole spans
        spans[0].logs[0].fields = None
        expected_spans[0].logs[0].fields = None

        self.assertEqual(spans, expected_spans)

    @patch("opentelemetry.exporter.jaeger.thrift.trace._TRACER_PROVIDER", None)
    def test_export(self):

        """Test that agent and/or collector are invoked"""

        trace_api.set_tracer_provider(
            TracerProvider(
                resource=Resource.create({SERVICE_NAME: "text_export"})
            )
        )

        exporter = jaeger_exporter.JaegerExporter(
            agent_host_name="localhost", agent_port=6318
        )

        # just agent is configured now
        agent_client_mock = mock.Mock(spec=jaeger_exporter.AgentClientUDP)
        # pylint: disable=protected-access
        exporter._agent_client = agent_client_mock

        exporter.export((self._test_span,))
        self.assertEqual(agent_client_mock.emit.call_count, 1)

        # add also a collector and test that both are called
        collector_mock = mock.Mock(spec=jaeger_exporter.Collector)
        # pylint: disable=protected-access
        exporter._collector = collector_mock

        exporter.export((self._test_span,))
        self.assertEqual(agent_client_mock.emit.call_count, 1)
        self.assertEqual(collector_mock.submit.call_count, 1)
        # trace_api._TRACER_PROVIDER = None

    @patch("opentelemetry.exporter.jaeger.thrift.trace._TRACER_PROVIDER", None)
    def test_export_span_service_name(self):
        trace_api.set_tracer_provider(
            TracerProvider(
                resource=Resource.create({SERVICE_NAME: "text_export"})
            )
        )
        exporter = jaeger_exporter.JaegerExporter(
            agent_host_name="localhost", agent_port=6318
        )
        agent_client_mock = mock.Mock(spec=jaeger_exporter.AgentClientUDP)
        exporter._agent_client = agent_client_mock
        resource = Resource.create({SERVICE_NAME: "test"})
        span = trace._Span(
            "test_span", context=self.context, resource=resource
        )
        span.start()
        span.end()
        exporter.export([span])
        self.assertEqual(exporter.service_name, "test")

    def test_agent_client(self):
        agent_client = jaeger_exporter.AgentClientUDP(
            host_name="localhost", port=6354
        )

        translate = Translate([self._test_span])
        # pylint: disable=protected-access
        spans = translate._translate(ThriftTranslator())

        batch = jaeger.Batch(
            spans=spans,
            process=jaeger.Process(serviceName="xxx"),
        )

        agent_client.emit(batch)

    def test_max_tag_value_length(self):
        span = trace._Span(
            name="span",
            resource=Resource(
                attributes={
                    "key_resource": "some_resource some_resource some_more_resource"
                }
            ),
            context=trace_api.SpanContext(
                trace_id=0x000000000000000000000000DEADBEEF,
                span_id=0x00000000DEADBEF0,
                is_remote=False,
            ),
        )

        span.start()
        span.set_attribute("key_bool", False)
        span.set_attribute("key_string", "hello_world hello_world hello_world")
        span.set_attribute("key_float", 111.22)
        span.set_attribute("key_int", 1100)
        span.set_attribute("key_tuple", ("tuple_element", "tuple_element2"))
        span.end()

        translate = Translate([span])

        # does not truncate by default
        # pylint: disable=protected-access
        spans = translate._translate(ThriftTranslator())
        tags_by_keys = {
            tag.key: tag.vStr
            for tag in spans[0].tags
            if tag.vType == jaeger.TagType.STRING
        }
        self.assertEqual(
            "hello_world hello_world hello_world", tags_by_keys["key_string"]
        )
        self.assertEqual(
            "('tuple_element', 'tuple_element2')", tags_by_keys["key_tuple"]
        )
        self.assertEqual(
            "some_resource some_resource some_more_resource",
            tags_by_keys["key_resource"],
        )

        # truncates when max_tag_value_length is passed
        # pylint: disable=protected-access
        spans = translate._translate(ThriftTranslator(max_tag_value_length=5))
        tags_by_keys = {
            tag.key: tag.vStr
            for tag in spans[0].tags
            if tag.vType == jaeger.TagType.STRING
        }
        self.assertEqual("hello", tags_by_keys["key_string"])
        self.assertEqual("('tup", tags_by_keys["key_tuple"])
        self.assertEqual("some_", tags_by_keys["key_resource"])

    def test_dropped_span_attributes(self):
        spans = _translate_spans_with_dropped_attributes()
        tags_by_keys = {
            tag.key: tag.vLong
            for tag in spans[0].tags
            if tag.vType == jaeger.TagType.LONG
        }

        self.assertEqual(1, tags_by_keys["otel.dropped_links_count"])
        self.assertEqual(2, tags_by_keys["otel.dropped_attributes_count"])
        self.assertEqual(3, tags_by_keys["otel.dropped_events_count"])

    def test_dropped_event_attributes(self):
        spans = _translate_spans_with_dropped_attributes()
        tags_by_keys = {
            tag.key: tag.vLong
            for tag in spans[0].logs[0].fields
            if tag.vType == jaeger.TagType.LONG
        }
        self.assertEqual(
            2,
            tags_by_keys["otel.dropped_attributes_count"],
        )

    def test_agent_client_split(self):
        agent_client = jaeger_exporter.AgentClientUDP(
            host_name="localhost",
            port=6354,
            max_packet_size=250,
            split_oversized_batches=True,
        )

        translator = jaeger_exporter.Translate((self._test_span,))
        small_batch = jaeger.Batch(
            # pylint: disable=protected-access
            spans=translator._translate(ThriftTranslator()),
            process=jaeger.Process(serviceName="xxx"),
        )

        with unittest.mock.patch(
            "socket.socket.sendto", autospec=True
        ) as fake_sendto:
            agent_client.emit(small_batch)
            self.assertEqual(fake_sendto.call_count, 1)

        translator = jaeger_exporter.Translate([self._test_span] * 2)
        large_batch = jaeger.Batch(
            # pylint: disable=protected-access
            spans=translator._translate(ThriftTranslator()),
            process=jaeger.Process(serviceName="xxx"),
        )

        with unittest.mock.patch(
            "socket.socket.sendto", autospec=True
        ) as fake_sendto:
            agent_client.emit(large_batch)
            self.assertEqual(fake_sendto.call_count, 2)

    def test_agent_client_dont_send_empty_spans(self):
        agent_client = jaeger_exporter.AgentClientUDP(
            host_name="localhost",
            port=6354,
            max_packet_size=415,
            split_oversized_batches=True,
        )

        translator = jaeger_exporter.Translate([self._test_span] * 4)
        large_batch = jaeger.Batch(
            # pylint: disable=protected-access
            spans=translator._translate(ThriftTranslator()),
            process=jaeger.Process(serviceName="xxx"),
        )

        with unittest.mock.patch(
            "socket.socket.sendto", autospec=True
        ) as fake_sendto:
            agent_client.emit(large_batch)
            self.assertEqual(fake_sendto.call_count, 4)
