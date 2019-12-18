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

from flask import Flask
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

import opentelemetry.ext.flask as otel_flask
from opentelemetry import trace as trace_api
from opentelemetry import propagation
from opentelemetry.ext.testutil.wsgitestutil import WsgiTestBase
from opentelemetry.sdk.context.propagation.tracecontexthttptextformat import (
    http_propagator,
)


class TestFlaskIntegration(WsgiTestBase):
    @classmethod
    def setUpClass(cls):
        """ Set preferred propagators """
        extractor, injector = http_propagator()
        # Save current propagator to be restored on teardown.
        cls._previous_injectors = propagation.get_http_injectors()
        cls._previous_extractors = propagation.get_http_extractors()

        propagation.set_http_extractors([extractor])
        propagation.set_http_injectors([injector])

    @classmethod
    def tearDownClass(cls):
        """ Restore previous propagator """
        propagation.set_http_extractors(cls._previous_extractors)
        propagation.set_http_injectors(cls._previous_injectors)

    def setUp(self):
        super().setUp()

        self.span_attrs = {}

        def setspanattr(key, value):
            self.assertIsInstance(key, str)
            self.span_attrs[key] = value

        self.span.set_attribute = setspanattr

        self.app = Flask(__name__)

        def hello_endpoint(helloid):
            if helloid == 500:
                raise ValueError(":-(")
            return "Hello: " + str(helloid)

        self.app.route("/hello/<int:helloid>")(hello_endpoint)

        otel_flask.instrument_app(self.app)
        self.client = Client(self.app, BaseResponse)

    def test_simple(self):
        resp = self.client.get("/hello/123")
        self.assertEqual(200, resp.status_code)
        self.assertEqual([b"Hello: 123"], list(resp.response))

        self.start_span.assert_called_with(
            "hello_endpoint",
            trace_api.INVALID_SPAN_CONTEXT,
            kind=trace_api.SpanKind.SERVER,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.server_name": "localhost",
                "http.scheme": "http",
                "host.port": 80,
                "http.host": "localhost",
                "http.target": "/hello/123",
                "http.flavor": "1.1",
                "http.route": "/hello/<int:helloid>",
            },
            start_time=mock.ANY,
        )

        # TODO: Change this test to use the SDK, as mocking becomes painful

        self.assertEqual(
            self.span_attrs,
            {"http.status_code": 200, "http.status_text": "OK"},
        )

    def test_404(self):
        resp = self.client.post("/bye")
        self.assertEqual(404, resp.status_code)
        resp.close()

        self.start_span.assert_called_with(
            "/bye",
            trace_api.INVALID_SPAN_CONTEXT,
            kind=trace_api.SpanKind.SERVER,
            attributes={
                "component": "http",
                "http.method": "POST",
                "http.server_name": "localhost",
                "http.scheme": "http",
                "host.port": 80,
                "http.host": "localhost",
                "http.target": "/bye",
                "http.flavor": "1.1",
            },
            start_time=mock.ANY,
        )

        # Nope, this uses Tracer.use_span(end_on_exit)
        #  self.assertEqual(1, self.span.end.call_count)
        # TODO: Change this test to use the SDK, as mocking becomes painful

        self.assertEqual(
            self.span_attrs,
            {"http.status_code": 404, "http.status_text": "NOT FOUND"},
        )

    def test_internal_error(self):
        resp = self.client.get("/hello/500")
        self.assertEqual(500, resp.status_code)
        resp.close()

        self.start_span.assert_called_with(
            "hello_endpoint",
            trace_api.INVALID_SPAN_CONTEXT,
            kind=trace_api.SpanKind.SERVER,
            attributes={
                "component": "http",
                "http.method": "GET",
                "http.server_name": "localhost",
                "http.scheme": "http",
                "host.port": 80,
                "http.host": "localhost",
                "http.target": "/hello/500",
                "http.flavor": "1.1",
                "http.route": "/hello/<int:helloid>",
            },
            start_time=mock.ANY,
        )

        # Nope, this uses Tracer.use_span(end_on_exit)
        #  self.assertEqual(1, self.span.end.call_count)
        # TODO: Change this test to use the SDK, as mocking becomes painful

        self.assertEqual(
            self.span_attrs,
            {
                "http.status_code": 500,
                "http.status_text": "INTERNAL SERVER ERROR",
            },
        )


if __name__ == "__main__":
    unittest.main()
