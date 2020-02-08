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

import sys
import unittest
import unittest.mock as mock
from urllib.parse import urlsplit

import opentelemetry.ext.asgi as otel_asgi
from opentelemetry import trace as trace_api
from opentelemetry.ext.testutil.asgitestutil import (
    AsgiTestBase, setup_testing_defaults
)


async def simple_asgi(scope, receive, send):
    assert isinstance(scope, dict)
    assert scope.get('type') == "http"
    payload = await receive()
    if payload.get('type') == "http.request":
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'Content-Type', b'text/plain'],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': b"*"
        })


async def error_asgi(scope, receive, send):
    assert isinstance(scope, dict)
    assert scope.get('type') == "http"
    payload = await receive()
    if payload.get('type') == "http.request":
        try:
            raise ValueError
        except ValueError:
            scope['hack_exc_info'] = sys.exc_info()
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'Content-Type', b'text/plain'],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': b"*"
        })


class TestAsgiApplication(AsgiTestBase):
    def validate_outputs(self, outputs, error=None):
        # Check for expected outputs
        self.assertEqual(len(outputs), 2)
        response_start = outputs[0]
        response_body = outputs[1]
        self.assertEqual(response_start['type'], 'http.response.start')
        self.assertEqual(response_body['type'], 'http.response.body')

        # Check http response body
        self.assertEqual(response_body['body'], b"*")

        # Check http response start
        self.assertEqual(response_start['status'], 200)
        self.assertEqual(response_start['headers'], [[b'Content-Type', b'text/plain']])

        exc_info = self.scope.get('hack_exc_info')
        if error:
            self.assertIs(exc_info[0], error)
            self.assertIsInstance(exc_info[1], error)
            self.assertIsNotNone(exc_info[2])
        else:
            self.assertIsNone(exc_info)

        # Check spans
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 4)
        expected = [
            {
                'name': "/ (http.request)",
                'kind': trace_api.SpanKind.INTERNAL,
                'attributes': {
                    "type": "http.request",
                },
            },

            {
                'name': "/ (http.response.start)",
                'kind': trace_api.SpanKind.INTERNAL,
                'attributes': {
                    "http.status_code": 200,
                    "type": "http.response.start",
                },
            },
            {
                'name': "/ (http.response.body)",
                'kind': trace_api.SpanKind.INTERNAL,
                'attributes': {
                    "type": "http.response.body",
                },
            },
            {
                'name': "/",
                'kind': trace_api.SpanKind.SERVER,
                'attributes': {
                    "component": "http",
                    "http.method": "GET",
                    "http.server_name": "127.0.0.1",
                    "http.scheme": "http",
                    "host.port": 80,
                    "http.host": "127.0.0.1",
                    "http.flavor": "1.0",
                    "http.target": "/",
                    "http.url": "http://127.0.0.1/",
                    "net.peer.ip": "127.0.0.1",
                    "net.peer.port": 32767,
                },
            },
        ]
        for span, expected in zip(span_list, expected):
            self.assertEqual(span.name, expected['name'])
            self.assertEqual(span.kind, expected['kind'])
            self.assertEqual(span.attributes, expected['attributes'])

    def test_basic_asgi_call(self):
        app = otel_asgi.OpenTelemetryMiddleware(simple_asgi)
        self.seed_app(app)
        self.send_default_request()
        outputs = self.get_all_output()
        self.validate_outputs(outputs)

    def test_wsgi_exc_info(self):
        app = otel_asgi.OpenTelemetryMiddleware(error_asgi)
        self.seed_app(app)
        self.send_default_request()
        outputs = self.get_all_output()
        self.validate_outputs(outputs, error=ValueError)


class TestAsgiAttributes(unittest.TestCase):
    def setUp(self):
        self.scope = {}
        setup_testing_defaults(self.scope)
        self.span = mock.create_autospec(trace_api.Span, spec_set=True)

    def test_request_attributes(self):
        self.scope["query_string"] = b"foo=bar"

        attrs = otel_asgi.collect_request_attributes(self.scope)
        self.assertDictEqual(
            attrs,
            {
                "component": "http",
                "http.method": "GET",
                "http.host": "127.0.0.1",
                "http.target": "/",
                "http.url": "http://127.0.0.1/?foo=bar",
                "host.port": 80,
                "http.scheme": "http",
                "http.server_name": "127.0.0.1",
                "http.flavor": "1.0",
                "net.peer.ip": "127.0.0.1",
                "net.peer.port": 32767
            },
        )

    def test_response_attributes(self):
        otel_asgi.set_status_code(self.span, 404)
        expected = (
            mock.call("http.status_code", 404),
        )
        self.assertEqual(self.span.set_attribute.call_count, 1)
        self.assertEqual(self.span.set_attribute.call_count, 1)
        self.span.set_attribute.assert_has_calls(expected, any_order=True)

    def test_response_attributes_invalid_status_code(self):
        otel_asgi.set_status_code(self.span, "Invalid Status Code")
        self.assertEqual(self.span.set_status.call_count, 1)


if __name__ == "__main__":
    unittest.main()
