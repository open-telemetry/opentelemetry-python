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
from unittest.mock import MagicMock, patch

from opentelemetry import trace as trace_api
from opentelemetry.ext.zipkin import ZipkinSpanExporter
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace import TraceFlags


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

        self._test_span = trace.Span("test_span", context=context)
        self._test_span.start()
        self._test_span.end()

    def test_constructor_default(self):
        """Test the default values assigned by constructor."""
        service_name = "my-service-name"
        host_name = "localhost"
        port = 9411
        endpoint = "/api/v2/spans"
        exporter = ZipkinSpanExporter(service_name)
        ipv4 = None
        ipv6 = None
        protocol = "http"
        url = "http://localhost:9411/api/v2/spans"

        self.assertEqual(exporter.service_name, service_name)
        self.assertEqual(exporter.host_name, host_name)
        self.assertEqual(exporter.port, port)
        self.assertEqual(exporter.endpoint, endpoint)
        self.assertEqual(exporter.ipv4, ipv4)
        self.assertEqual(exporter.ipv6, ipv6)
        self.assertEqual(exporter.protocol, protocol)
        self.assertEqual(exporter.url, url)

    def test_constructor_explicit(self):
        """Test the constructor passing all the options."""
        service_name = "my-opentelemetry-zipkin"
        host_name = "opentelemetry.io"
        port = 15875
        endpoint = "/myapi/traces?format=zipkin"
        ipv4 = "1.2.3.4"
        ipv6 = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        protocol = "https"
        url = "https://opentelemetry.io:15875/myapi/traces?format=zipkin"
        exporter = ZipkinSpanExporter(
            service_name=service_name,
            host_name=host_name,
            port=port,
            endpoint=endpoint,
            ipv4=ipv4,
            ipv6=ipv6,
            protocol=protocol,
        )

        self.assertEqual(exporter.service_name, service_name)
        self.assertEqual(exporter.host_name, host_name)
        self.assertEqual(exporter.port, port)
        self.assertEqual(exporter.endpoint, endpoint)
        self.assertEqual(exporter.ipv4, ipv4)
        self.assertEqual(exporter.ipv6, ipv6)
        self.assertEqual(exporter.protocol, protocol)
        self.assertEqual(exporter.url, url)

    # pylint: disable=too-many-locals
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
            trace_id,
            span_id,
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        parent_context = trace_api.SpanContext(
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
            ),
            trace.Span(
                name=span_names[1], context=parent_context, parent=None
            ),
            trace.Span(name=span_names[2], context=other_context, parent=None),
        ]

        otel_spans[0].start(start_time=start_times[0])
        # added here to preserve order
        otel_spans[0].set_attribute("key_bool", False)
        otel_spans[0].set_attribute("key_string", "hello_world")
        otel_spans[0].set_attribute("key_float", 111.22)
        otel_spans[0].end(end_time=end_times[0])

        otel_spans[1].start(start_time=start_times[1])
        otel_spans[1].end(end_time=end_times[1])

        otel_spans[2].start(start_time=start_times[2])
        otel_spans[2].end(end_time=end_times[2])

        service_name = "test-service"
        local_endpoint = {"serviceName": service_name, "port": 9411}

        exporter = ZipkinSpanExporter(service_name)
        expected = [
            {
                "traceId": format(trace_id, "x"),
                "id": format(span_id, "x"),
                "name": span_names[0],
                "timestamp": start_times[0] // 10 ** 3,
                "duration": durations[0] // 10 ** 3,
                "localEndpoint": local_endpoint,
                "kind": None,
                "tags": {
                    "key_bool": "False",
                    "key_string": "hello_world",
                    "key_float": "111.22",
                },
                "annotations": [
                    {
                        "timestamp": event_timestamp // 10 ** 3,
                        "value": "event0",
                    }
                ],
                "debug": 1,
                "parentId": format(parent_id, "x"),
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(parent_id, "x"),
                "name": span_names[1],
                "timestamp": start_times[1] // 10 ** 3,
                "duration": durations[1] // 10 ** 3,
                "localEndpoint": local_endpoint,
                "kind": None,
                "tags": None,
                "annotations": None,
            },
            {
                "traceId": format(trace_id, "x"),
                "id": format(other_id, "x"),
                "name": span_names[2],
                "timestamp": start_times[2] // 10 ** 3,
                "duration": durations[2] // 10 ** 3,
                "localEndpoint": local_endpoint,
                "kind": None,
                "tags": None,
                "annotations": None,
            },
        ]

        mock_post = MagicMock()
        with patch("requests.post", mock_post):
            mock_post.return_value = MockResponse(200)
            status = exporter.export(otel_spans)
            self.assertEqual(SpanExportResult.SUCCESS, status)

        mock_post.assert_called_with(
            url="http://localhost:9411/api/v2/spans",
            data=json.dumps(expected),
            headers={"Content-Type": "application/json"},
        )

    @patch("requests.post")
    def test_invalid_response(self, mock_post):
        mock_post.return_value = MockResponse(404)
        spans = []
        exporter = ZipkinSpanExporter("test-service")
        status = exporter.export(spans)
        self.assertEqual(SpanExportResult.FAILED_NOT_RETRYABLE, status)
