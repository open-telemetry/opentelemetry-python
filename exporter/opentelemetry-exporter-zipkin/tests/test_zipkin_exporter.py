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
import os
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry import trace as trace_api
from opentelemetry.configuration import Configuration
from opentelemetry.exporter.zipkin import TransportFormat, ZipkinSpanExporter
from opentelemetry.exporter.zipkin.endpoint import LocalEndpoint
from opentelemetry.exporter.zipkin.transport_formatter import TransportFormatter
import opentelemetry.exporter.zipkin.transport_formatter.v1.json as v1_json
import opentelemetry.exporter.zipkin.transport_formatter.v2.json as v2_json
import opentelemetry.exporter.zipkin.transport_formatter.v2.protobuf as \
    v2_protobuf
from opentelemetry.exporter.zipkin.transport_formatter.v2.protobuf.gen import (
    zipkin_pb2
)
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace import Resource
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo
from opentelemetry.trace import SpanKind, TraceFlags
from opentelemetry.trace.status import Status, StatusCode


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = status_code


class TestZipkinSpanExporter(unittest.TestCase):
    def setUp(self):
        # create and save span to be used in tests
        context = trace_api.SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000DEADBEF0,
            is_remote=False,
        )

        self._test_span = trace._Span("test_span", context=context)
        self._test_span.start()
        self._test_span.end()

    def tearDown(self):
        if "OTEL_EXPORTER_ZIPKIN_ENDPOINT" in os.environ:
            del os.environ["OTEL_EXPORTER_ZIPKIN_ENDPOINT"]
        if "OTEL_EXPORTER_ZIPKIN_TRANSPORT_FORMAT" in os.environ:
            del os.environ["OTEL_EXPORTER_ZIPKIN_TRANSPORT_FORMAT"]
        Configuration()._reset()  # pylint: disable=protected-access

    def test_constructor_env_var(self):
        """Test the default values assigned by constructor."""
        url = "https://foo:9911/path"
        os.environ["OTEL_EXPORTER_ZIPKIN_ENDPOINT"] = url
        os.environ[
            "OTEL_EXPORTER_ZIPKIN_TRANSPORT_FORMAT"
        ] = TransportFormat.V2_PROTOBUF.value
        service_name = "my-service-name"
        exporter = ZipkinSpanExporter(LocalEndpoint(service_name))

        self.assertEqual(exporter.local_endpoint.service_name, service_name)
        self.assertEqual(exporter.local_endpoint.ipv4, None)
        self.assertEqual(exporter.local_endpoint.ipv6, None)
        self.assertEqual(exporter.local_endpoint.url, url)
        self.assertEqual(exporter.local_endpoint.port, 9911)
        self.assertEqual(
            exporter.transport_format, TransportFormat.V2_PROTOBUF
        )

    def test_constructor_default(self):
        """Test the default values assigned by constructor."""
        service_name = "my-service-name"
        exporter = ZipkinSpanExporter(LocalEndpoint(service_name))

        self.assertEqual(exporter.local_endpoint.service_name, service_name)
        self.assertEqual(exporter.local_endpoint.port, 9411)
        self.assertEqual(exporter.local_endpoint.ipv4, None)
        self.assertEqual(exporter.local_endpoint.ipv6, None)
        self.assertEqual(exporter.local_endpoint.url, "http://localhost:9411/api/v2/spans")
        self.assertEqual(exporter.transport_format, TransportFormat.V2_JSON)

    def test_constructor_explicit(self):
        """Test the constructor passing all the options."""
        service_name = "my-opentelemetry-zipkin"
        port = 15875
        ipv4 = "1.2.3.4"
        ipv6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        url = "https://opentelemetry.io:15875/myapi/traces?format=zipkin"
        transport_format = TransportFormat.V2_PROTOBUF

        exporter = ZipkinSpanExporter(
            LocalEndpoint(
                service_name=service_name,
                url=url,
                ipv4=ipv4,
                ipv6=ipv6,
            ),
            transport_format=transport_format,
        )

        self.assertEqual(exporter.local_endpoint.service_name, service_name)
        self.assertEqual(exporter.local_endpoint.port, port)
        self.assertEqual(exporter.local_endpoint.ipv4, ipv4)
        self.assertEqual(exporter.local_endpoint.ipv6, ipv6)
        self.assertEqual(exporter.local_endpoint.url, url)
        self.assertEqual(exporter.transport_format, transport_format)


    @patch("requests.post")
    def test_invalid_response(self, mock_post):
        mock_post.return_value = MockResponse(404)
        spans = []
        exporter = ZipkinSpanExporter(LocalEndpoint("test-service"))
        status = exporter.export(spans)
        self.assertEqual(SpanExportResult.FAILURE, status)

    # pylint: disable=too-many-locals,too-many-statements
    def test_export_v1_json(self):
        span_names = ("test1", "test2", "test3", "test4")
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        parent_id = 0x1111111111111111
        other_id = 0x2222222222222222

        base_time = 683647322 * 10 ** 9  # in ns
        start_times = (
            base_time,
            base_time + 150 * 10 ** 6,
            base_time + 300 * 10 ** 6,
            base_time + 400 * 10 ** 6,
        )
        durations = (50 * 10 ** 6, 100 * 10 ** 6, 200 * 10 ** 6, 300 * 10 ** 6)
        end_times = (
            start_times[0] + durations[0],
            start_times[1] + durations[1],
            start_times[2] + durations[2],
            start_times[3] + durations[3],
        )

        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
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

        otel_spans = [
            trace._Span(
                name=span_names[0],
                context=span_context,
                parent=parent_span_context,
                events=(event,),
                links=(link,),
            ),
            trace._Span(
                name=span_names[1], context=parent_span_context, parent=None
            ),
            trace._Span(
                name=span_names[2], context=other_context, parent=None
            ),
            trace._Span(
                name=span_names[3], context=other_context, parent=None
            ),
        ]

        otel_spans[0].start(start_time=start_times[0])
        otel_spans[0].resource = Resource({})
        # added here to preserve order
        otel_spans[0].set_attribute("key_bool", False)
        otel_spans[0].set_attribute("key_string", "hello_world")
        otel_spans[0].set_attribute("key_float", 111.22)
        otel_spans[0].set_status(
            Status(StatusCode.ERROR, "Example description")
        )
        otel_spans[0].end(end_time=end_times[0])

        otel_spans[1].start(start_time=start_times[1])
        otel_spans[1].resource = Resource(
            attributes={"key_resource": "some_resource"}
        )
        otel_spans[1].end(end_time=end_times[1])

        otel_spans[2].start(start_time=start_times[2])
        otel_spans[2].set_attribute("key_string", "hello_world")
        otel_spans[2].resource = Resource(
            attributes={"key_resource": "some_resource"}
        )
        otel_spans[2].end(end_time=end_times[2])

        otel_spans[3].start(start_time=start_times[3])
        otel_spans[3].resource = Resource({})
        otel_spans[3].end(end_time=end_times[3])
        otel_spans[3].instrumentation_info = InstrumentationInfo(
            name="name", version="version"
        )

        service_name = "test-service"
        local_endpoint = {"serviceName": service_name, "port": 9411}

        expected_spans = [
            {
                "traceId": format(trace_id, "x"),
                "id": format(span_id, "x"),
                "name": span_names[0],
                "timestamp": start_times[0] // 10 ** 3,
                "duration": durations[0] // 10 ** 3,
                "annotations": [
                    {
                        "timestamp": event_timestamp // 10 ** 3,
                        "value": {
                            "event0": {
                                "annotation_bool": True,
                                "annotation_string": "annotation_test",
                                "key_float": 0.3,
                            }
                        },
                        "endpoint": local_endpoint,
                    }
                ],
                "binaryAnnotations": [
                    {
                        "key": "key_bool",
                        "value": "False",
                        "endpoint": local_endpoint
                    },
                    {
                        "key": "key_string",
                        "value": "hello_world",
                        "endpoint": local_endpoint
                    },
                    {
                        "key": "key_float",
                        "value": "111.22",
                        "endpoint": local_endpoint
                    },
                    {
                        "key": "otel.status_code",
                        "value": "2",
                        "endpoint": local_endpoint
                    },
                    {
                        "key": "otel.status_description",
                        "value": "Example description",
                        "endpoint": local_endpoint
                    },
                ],
                "debug": True,
                "parentId": format(parent_id, "x"),
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(parent_id, "x"),
                "name": span_names[1],
                "timestamp": start_times[1] // 10 ** 3,
                "duration": durations[1] // 10 ** 3,
                "annotations": None,
                "binaryAnnotations": [
                    {
                        "key": "key_resource",
                        "value": "some_resource",
                        "endpoint": local_endpoint
                    },
                    {
                        "key": "otel.status_code",
                        "value": "1",
                        "endpoint": local_endpoint
                    },
                ],
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(other_id, "x"),
                "name": span_names[2],
                "timestamp": start_times[2] // 10 ** 3,
                "duration": durations[2] // 10 ** 3,
                "annotations": None,
                "binaryAnnotations": [
                    {
                        "key": "key_string",
                        "value": "hello_world",
                        "endpoint": local_endpoint
                    },
                    {
                        "key": "key_resource",
                        "value": "some_resource",
                        "endpoint": local_endpoint
                    },
                    {
                        "key": "otel.status_code",
                        "value": "1",
                        "endpoint": local_endpoint
                    },
                ],
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(other_id, "x"),
                "name": span_names[3],
                "timestamp": start_times[3] // 10 ** 3,
                "duration": durations[3] // 10 ** 3,
                "annotations": None,
                "binaryAnnotations": [
                    {
                        "key": "otel.instrumentation_library.name",
                        "value": "name",
                        "endpoint": local_endpoint
                    },
                    {
                        "key": "otel.instrumentation_library.version",
                        "value": "version",
                        "endpoint": local_endpoint
                    },
                    {
                        "key": "otel.status_code",
                        "value": "1",
                        "endpoint": local_endpoint
                    },
                ],
            },
        ]

        exporter = ZipkinSpanExporter(
            LocalEndpoint(
                service_name,
                url="http://localhost:9411/api/v1/spans",
            ),
            transport_format=TransportFormat.V1_JSON,
        )
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export(otel_spans)
            self.assertEqual(SpanExportResult.SUCCESS, status)

        # pylint: disable=unsubscriptable-object
        kwargs = mock_post.call_args[1]

        self.assertEqual(kwargs["url"], "http://localhost:9411/api/v1/spans")
        self.assertEqual(
            kwargs["headers"]["Content-Type"],
            v1_json.V1JsonTransportFormatter.http_content_type()
        )
        actual_spans = sorted(
            json.loads(kwargs["data"]), key=lambda span: span["timestamp"]
        )

        for expected, actual in zip(expected_spans, actual_spans):
            expected_annotations = expected.pop("annotations", None)
            actual_annotations = actual.pop("annotations", None)
            if actual_annotations:
                for annotation in actual_annotations:
                    annotation["value"] = json.loads(annotation["value"])

            self.assertEqual(expected, actual)
            self.assertEqual(expected_annotations, actual_annotations)

    # pylint: disable=too-many-locals
    def test_export_v1_json_zero_padding(self):
        """test that hex ids starting with 0
        are properly padded to 16 or 32 hex chars
        when exported
        """

        span_names = "testZeroes"
        trace_id = 0x0E0C63257DE34C926F9EFCD03927272E
        span_id = 0x04BF92DEEFC58C92
        parent_id = 0x0AAAAAAAAAAAAAAA

        start_time = 683647322 * 10 ** 9  # in ns
        duration = 50 * 10 ** 6
        end_time = start_time + duration

        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        parent_span_context = trace_api.SpanContext(
            trace_id, parent_id, is_remote=False
        )

        otel_span = trace._Span(
            name=span_names[0],
            context=span_context,
            parent=parent_span_context,
        )

        otel_span.start(start_time=start_time)
        otel_span.resource = Resource({})
        otel_span.end(end_time=end_time)

        service_name = "test-service"
        local_endpoint = {"serviceName": service_name, "port": 9411}

        # Check traceId are properly lowercase 16 or 32 hex
        expected = [
            {
                "traceId": "0e0c63257de34c926f9efcd03927272e",
                "id": "04bf92deefc58c92",
                "name": span_names[0],
                "timestamp": start_time // 10 ** 3,
                "duration": duration // 10 ** 3,
                "annotations": None,
                "binaryAnnotations": [
                    {
                        "key": "otel.status_code",
                        "value": "1",
                        "endpoint": local_endpoint,
                    },
                ],
                "debug": True,
                "parentId": "0aaaaaaaaaaaaaaa",
            }
        ]

        exporter = ZipkinSpanExporter(
            LocalEndpoint(
                service_name,
                url="http://localhost:9411/api/v1/spans",
            ),
            transport_format=TransportFormat.V1_JSON,
        )
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export([otel_span])
            self.assertEqual(SpanExportResult.SUCCESS, status)

        mock_post.assert_called_with(
            url="http://localhost:9411/api/v1/spans",
            data=json.dumps(expected),
            headers=
            {
                "Content-Type":
                          v1_json.V1JsonTransportFormatter.http_content_type()
            },
        )

    def test_export_v1_json_max_tag_length(self):
        service_name = "test-service"

        span_context = trace_api.SpanContext(
            0x0E0C63257DE34C926F9EFCD03927272E,
            0x04BF92DEEFC58C92,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )

        span = trace._Span(name="test-span", context=span_context,)

        span.start()
        span.resource = Resource({})
        # added here to preserve order
        span.set_attribute("k1", "v" * 500)
        span.set_attribute("k2", "v" * 50)
        span.set_status(Status(StatusCode.ERROR, "Example description"))
        span.end()

        exporter = ZipkinSpanExporter(
            LocalEndpoint(
                service_name,
                url="http://localhost:9411/api/v1/spans",
            ),
            transport_format=TransportFormat.V1_JSON,
        )
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export([span])
            self.assertEqual(SpanExportResult.SUCCESS, status)

        _, kwargs = mock_post.call_args  # pylint: disable=E0633

        binary_annotations = json.loads(kwargs["data"])[0]["binaryAnnotations"]
        self.assertEqual(len(binary_annotations[0]["value"]), 128)
        self.assertEqual(len(binary_annotations[1]["value"]), 50)

        exporter = ZipkinSpanExporter(
            LocalEndpoint(
                service_name,
                url="http://localhost:9411/api/v1/spans",
            ),
            transport_format=TransportFormat.V1_JSON,
            max_tag_value_length=2,
        )
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export([span])
            self.assertEqual(SpanExportResult.SUCCESS, status)

        _, kwargs = mock_post.call_args  # pylint: disable=E0633
        binary_annotations = json.loads(kwargs["data"])[0]["binaryAnnotations"]
        self.assertEqual(len(binary_annotations[0]["value"]), 2)
        self.assertEqual(len(binary_annotations[1]["value"]), 2)

    # pylint: disable=too-many-locals,too-many-statements
    def test_export_v2_json(self):
        span_names = ("test1", "test2", "test3", "test4")
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        parent_id = 0x1111111111111111
        other_id = 0x2222222222222222

        base_time = 683647322 * 10 ** 9  # in ns
        start_times = (
            base_time,
            base_time + 150 * 10 ** 6,
            base_time + 300 * 10 ** 6,
            base_time + 400 * 10 ** 6,
        )
        durations = (50 * 10 ** 6, 100 * 10 ** 6, 200 * 10 ** 6, 300 * 10 ** 6)
        end_times = (
            start_times[0] + durations[0],
            start_times[1] + durations[1],
            start_times[2] + durations[2],
            start_times[3] + durations[3],
        )

        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
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

        otel_spans = [
            trace._Span(
                name=span_names[0],
                context=span_context,
                parent=parent_span_context,
                events=(event,),
                links=(link,),
            ),
            trace._Span(
                name=span_names[1], context=parent_span_context, parent=None
            ),
            trace._Span(
                name=span_names[2], context=other_context, parent=None
            ),
            trace._Span(
                name=span_names[3], context=other_context, parent=None
            ),
        ]

        otel_spans[0].start(start_time=start_times[0])
        otel_spans[0].resource = Resource({})
        # added here to preserve order
        otel_spans[0].set_attribute("key_bool", False)
        otel_spans[0].set_attribute("key_string", "hello_world")
        otel_spans[0].set_attribute("key_float", 111.22)
        otel_spans[0].set_status(
            Status(StatusCode.ERROR, "Example description")
        )
        otel_spans[0].end(end_time=end_times[0])

        otel_spans[1].start(start_time=start_times[1])
        otel_spans[1].resource = Resource(
            attributes={"key_resource": "some_resource"}
        )
        otel_spans[1].end(end_time=end_times[1])

        otel_spans[2].start(start_time=start_times[2])
        otel_spans[2].set_attribute("key_string", "hello_world")
        otel_spans[2].resource = Resource(
            attributes={"key_resource": "some_resource"}
        )
        otel_spans[2].end(end_time=end_times[2])

        otel_spans[3].start(start_time=start_times[3])
        otel_spans[3].resource = Resource({})
        otel_spans[3].end(end_time=end_times[3])
        otel_spans[3].instrumentation_info = InstrumentationInfo(
            name="name", version="version"
        )

        service_name = "test-service"
        local_endpoint = {"serviceName": service_name, "port": 9411}
        span_kind = v2_json.SPAN_KIND_MAP[SpanKind.INTERNAL]

        exporter = ZipkinSpanExporter(LocalEndpoint(service_name))
        expected_spans = [
            {
                "traceId": format(trace_id, "x"),
                "id": format(span_id, "x"),
                "name": span_names[0],
                "timestamp": start_times[0] // 10 ** 3,
                "duration": durations[0] // 10 ** 3,
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "key_bool": "False",
                    "key_string": "hello_world",
                    "key_float": "111.22",
                    "otel.status_code": "2",
                    "otel.status_description": "Example description",
                },
                "debug": True,
                "parentId": format(parent_id, "x"),
                "annotations": [
                    {
                        "timestamp": event_timestamp // 10 ** 3,
                        "value": {
                            "event0": {
                                "annotation_bool": True,
                                "annotation_string": "annotation_test",
                                "key_float": 0.3,
                            }
                        },
                    }
                ],
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(parent_id, "x"),
                "name": span_names[1],
                "timestamp": start_times[1] // 10 ** 3,
                "duration": durations[1] // 10 ** 3,
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "key_resource": "some_resource",
                    "otel.status_code": "1",
                },
                "annotations": None,
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(other_id, "x"),
                "name": span_names[2],
                "timestamp": start_times[2] // 10 ** 3,
                "duration": durations[2] // 10 ** 3,
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "key_string": "hello_world",
                    "key_resource": "some_resource",
                    "otel.status_code": "1",
                },
                "annotations": None,
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(other_id, "x"),
                "name": span_names[3],
                "timestamp": start_times[3] // 10 ** 3,
                "duration": durations[3] // 10 ** 3,
                "localEndpoint": local_endpoint,
                "kind": span_kind,
                "tags": {
                    "otel.instrumentation_library.name": "name",
                    "otel.instrumentation_library.version": "version",
                    "otel.status_code": "1",
                },
                "annotations": None,
            },
        ]

        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export(otel_spans)
            self.assertEqual(SpanExportResult.SUCCESS, status)

        # pylint: disable=unsubscriptable-object
        kwargs = mock_post.call_args[1]

        self.assertEqual(kwargs["url"], "http://localhost:9411/api/v2/spans")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        actual_spans = sorted(
            json.loads(kwargs["data"]), key=lambda span: span["timestamp"]
        )
        for expected, actual in zip(expected_spans, actual_spans):
            expected_annotations = expected.pop("annotations", None)
            actual_annotations = actual.pop("annotations", None)
            if actual_annotations:
                for annotation in actual_annotations:
                    annotation["value"] = json.loads(annotation["value"])
            self.assertEqual(expected, actual)
            self.assertEqual(expected_annotations, actual_annotations)

    # pylint: disable=too-many-locals
    def test_export_v2_json_zero_padding(self):
        """test that hex ids starting with 0
        are properly padded to 16 or 32 hex chars
        when exported
        """

        span_names = "testZeroes"
        trace_id = 0x0E0C63257DE34C926F9EFCD03927272E
        span_id = 0x04BF92DEEFC58C92
        parent_id = 0x0AAAAAAAAAAAAAAA

        start_time = 683647322 * 10 ** 9  # in ns
        duration = 50 * 10 ** 6
        end_time = start_time + duration

        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        parent_span_context = trace_api.SpanContext(
            trace_id, parent_id, is_remote=False
        )

        otel_span = trace._Span(
            name=span_names[0],
            context=span_context,
            parent=parent_span_context,
        )

        otel_span.start(start_time=start_time)
        otel_span.resource = Resource({})
        otel_span.end(end_time=end_time)

        service_name = "test-service"
        local_endpoint = {"serviceName": service_name, "port": 9411}

        exporter = ZipkinSpanExporter(LocalEndpoint(service_name))
        # Check traceId are properly lowercase 16 or 32 hex
        expected = [
            {
                "traceId": "0e0c63257de34c926f9efcd03927272e",
                "id": "04bf92deefc58c92",
                "name": span_names[0],
                "timestamp": start_time // 10 ** 3,
                "duration": duration // 10 ** 3,
                "localEndpoint": local_endpoint,
                "kind": v2_json.SPAN_KIND_MAP[SpanKind.INTERNAL],
                "tags": {"otel.status_code": "1"},
                "annotations": None,
                "debug": True,
                "parentId": "0aaaaaaaaaaaaaaa",
            }
        ]

        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export([otel_span])
            self.assertEqual(SpanExportResult.SUCCESS, status)

        mock_post.assert_called_with(
            url="http://localhost:9411/api/v2/spans",
            data=json.dumps(expected),
            headers={"Content-Type": "application/json"},
        )

    def test_export_v2_json_max_tag_length(self):
        service_name = "test-service"

        span_context = trace_api.SpanContext(
            0x0E0C63257DE34C926F9EFCD03927272E,
            0x04BF92DEEFC58C92,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )

        span = trace._Span(name="test-span", context=span_context,)

        span.start()
        span.resource = Resource({})
        # added here to preserve order
        span.set_attribute("k1", "v" * 500)
        span.set_attribute("k2", "v" * 50)
        span.set_status(Status(StatusCode.ERROR, "Example description"))
        span.end()

        exporter = ZipkinSpanExporter(LocalEndpoint(service_name))
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export([span])
            self.assertEqual(SpanExportResult.SUCCESS, status)

        _, kwargs = mock_post.call_args  # pylint: disable=E0633

        tags = json.loads(kwargs["data"])[0]["tags"]
        self.assertEqual(len(tags["k1"]), 128)
        self.assertEqual(len(tags["k2"]), 50)

        exporter = ZipkinSpanExporter(
            LocalEndpoint(service_name),
            max_tag_value_length=2,
        )
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export([span])
            self.assertEqual(SpanExportResult.SUCCESS, status)

        _, kwargs = mock_post.call_args  # pylint: disable=E0633
        tags = json.loads(kwargs["data"])[0]["tags"]
        self.assertEqual(len(tags["k1"]), 2)
        self.assertEqual(len(tags["k2"]), 2)

    # pylint: disable=too-many-locals,too-many-statements
    def test_export_v2_protobuf(self):
        span_names = ("test1", "test2", "test3", "test4")
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        parent_id = 0x1111111111111111
        other_id = 0x2222222222222222

        base_time = 683647322 * 10 ** 9  # in ns
        start_times = (
            base_time,
            base_time + 150 * 10 ** 6,
            base_time + 300 * 10 ** 6,
            base_time + 400 * 10 ** 6,
        )
        durations = (50 * 10 ** 6, 100 * 10 ** 6, 200 * 10 ** 6, 300 * 10 ** 6)
        end_times = (
            start_times[0] + durations[0],
            start_times[1] + durations[1],
            start_times[2] + durations[2],
            start_times[3] + durations[3],
        )

        span_context = trace_api.SpanContext(
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
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

        otel_spans = [
            trace._Span(
                name=span_names[0],
                context=span_context,
                parent=parent_span_context,
                events=(event,),
                links=(link,),
            ),
            trace._Span(
                name=span_names[1], context=parent_span_context, parent=None
            ),
            trace._Span(
                name=span_names[2], context=other_context, parent=None
            ),
            trace._Span(
                name=span_names[3], context=other_context, parent=None
            ),
        ]

        otel_spans[0].start(start_time=start_times[0])
        otel_spans[0].resource = Resource({})
        # added here to preserve order
        otel_spans[0].set_attribute("key_bool", False)
        otel_spans[0].set_attribute("key_string", "hello_world")
        otel_spans[0].set_attribute("key_float", 111.22)
        otel_spans[0].set_status(
            Status(StatusCode.ERROR, "Example description")
        )
        otel_spans[0].end(end_time=end_times[0])

        otel_spans[1].start(start_time=start_times[1])
        otel_spans[1].resource = Resource(
            attributes={"key_resource": "some_resource"}
        )
        otel_spans[1].end(end_time=end_times[1])

        otel_spans[2].start(start_time=start_times[2])
        otel_spans[2].set_attribute("key_string", "hello_world")
        otel_spans[2].resource = Resource(
            attributes={"key_resource": "some_resource"}
        )
        otel_spans[2].end(end_time=end_times[2])

        otel_spans[3].start(start_time=start_times[3])
        otel_spans[3].resource = Resource({})
        otel_spans[3].end(end_time=end_times[3])
        otel_spans[3].instrumentation_info = InstrumentationInfo(
            name="name", version="version"
        )

        service_name = "test-service"
        local_endpoint = zipkin_pb2.Endpoint(
            service_name=service_name, port=9411
        )
        span_kind = v2_protobuf.SPAN_KIND_MAP[SpanKind.INTERNAL]

        expected_spans = zipkin_pb2.ListOfSpans(
            spans=[
                zipkin_pb2.Span(
                    trace_id=trace_id.to_bytes(
                        length=16, byteorder="big", signed=False
                    ),
                    id=v2_protobuf.format_pbuf_span_id(span_id),
                    name=span_names[0],
                    timestamp=TransportFormatter.nsec_to_usec_round(
                        start_times[0]
                    ),
                    duration=TransportFormatter.nsec_to_usec_round(
                        durations[0]
                    ),
                    local_endpoint=local_endpoint,
                    kind=span_kind,
                    tags={
                        "key_bool": "False",
                        "key_string": "hello_world",
                        "key_float": "111.22",
                        "otel.status_code": "2",
                        "otel.status_description": "Example description",
                    },
                    debug=True,
                    parent_id=v2_protobuf.format_pbuf_span_id(
                        parent_id
                    ),
                    annotations=[
                        zipkin_pb2.Annotation(
                            timestamp=TransportFormatter.nsec_to_usec_round(
                                event_timestamp
                            ),
                            value=json.dumps(
                                {
                                    "event0": {
                                        "annotation_bool": True,
                                        "annotation_string": "annotation_test",
                                        "key_float": 0.3,
                                    }
                                }
                            ),
                        ),
                    ],
                ),
                zipkin_pb2.Span(
                    trace_id=trace_id.to_bytes(
                        length=16, byteorder="big", signed=False
                    ),
                    id=v2_protobuf.format_pbuf_span_id(parent_id),
                    name=span_names[1],
                    timestamp=TransportFormatter.nsec_to_usec_round(
                        start_times[1]
                    ),
                    duration=TransportFormatter.nsec_to_usec_round(
                        durations[1]
                    ),
                    local_endpoint=local_endpoint,
                    kind=span_kind,
                    tags={
                        "key_resource": "some_resource",
                        "otel.status_code": "1",
                    },
                ),
                zipkin_pb2.Span(
                    trace_id=trace_id.to_bytes(
                        length=16, byteorder="big", signed=False
                    ),
                    id=v2_protobuf.format_pbuf_span_id(other_id),
                    name=span_names[2],
                    timestamp=TransportFormatter.nsec_to_usec_round(
                        start_times[2]
                    ),
                    duration=TransportFormatter.nsec_to_usec_round(
                        durations[2]
                    ),
                    local_endpoint=local_endpoint,
                    kind=span_kind,
                    tags={
                        "key_string": "hello_world",
                        "key_resource": "some_resource",
                        "otel.status_code": "1",
                    },
                ),
                zipkin_pb2.Span(
                    trace_id=trace_id.to_bytes(
                        length=16, byteorder="big", signed=False
                    ),
                    id=v2_protobuf.format_pbuf_span_id(other_id),
                    name=span_names[3],
                    timestamp=TransportFormatter.nsec_to_usec_round(
                        start_times[3]
                    ),
                    duration=TransportFormatter.nsec_to_usec_round(
                        durations[3]
                    ),
                    local_endpoint=local_endpoint,
                    kind=span_kind,
                    tags={
                        "otel.instrumentation_library.name": "name",
                        "otel.instrumentation_library.version": "version",
                        "otel.status_code": "1",
                    },
                ),
            ],
        )

        exporter = ZipkinSpanExporter(
            LocalEndpoint(service_name),
            transport_format=TransportFormat.V2_PROTOBUF,
        )
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export(otel_spans)
            self.assertEqual(SpanExportResult.SUCCESS, status)

        # pylint: disable=unsubscriptable-object
        kwargs = mock_post.call_args[1]

        self.assertEqual(kwargs["url"], "http://localhost:9411/api/v2/spans")
        self.assertEqual(
            kwargs["headers"]["Content-Type"], "application/x-protobuf"
        )
        self.assertEqual(
            zipkin_pb2.ListOfSpans.FromString(kwargs["data"]), expected_spans
        )

    def test_export_v2_protobuf_max_tag_length(self):
        service_name = "test-service"

        span_context = trace_api.SpanContext(
            0x0E0C63257DE34C926F9EFCD03927272E,
            0x04BF92DEEFC58C92,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )

        span = trace._Span(name="test-span", context=span_context,)

        span.start()
        span.resource = Resource({})
        # added here to preserve order
        span.set_attribute("k1", "v" * 500)
        span.set_attribute("k2", "v" * 50)
        span.set_status(Status(StatusCode.ERROR, "Example description"))
        span.end()

        exporter = ZipkinSpanExporter(
            LocalEndpoint(service_name),
            transport_format=TransportFormat.V2_PROTOBUF,
        )
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export([span])
            self.assertEqual(SpanExportResult.SUCCESS, status)

        # pylint: disable=unsubscriptable-object
        kwargs = mock_post.call_args[1]
        actual_spans = zipkin_pb2.ListOfSpans.FromString(kwargs["data"])
        span_tags = actual_spans.spans[0].tags

        self.assertEqual(len(span_tags["k1"]), 128)
        self.assertEqual(len(span_tags["k2"]), 50)

        exporter = ZipkinSpanExporter(
            LocalEndpoint(service_name),
            transport_format=TransportFormat.V2_PROTOBUF,
            max_tag_value_length=2,
        )
        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export([span])
            self.assertEqual(SpanExportResult.SUCCESS, status)

        # pylint: disable=unsubscriptable-object
        kwargs = mock_post.call_args[1]
        actual_spans = zipkin_pb2.ListOfSpans.FromString(kwargs["data"])
        span_tags = actual_spans.spans[0].tags

        self.assertEqual(len(span_tags["k1"]), 2)
        self.assertEqual(len(span_tags["k2"]), 2)
