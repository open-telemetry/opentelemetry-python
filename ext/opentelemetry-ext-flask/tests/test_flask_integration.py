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

from flask import Flask
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

import opentelemetry.ext.flask as otel_flask
from opentelemetry import trace as trace_api
from opentelemetry.ext.testutil.wsgitestutil import WsgiTestBase


class TestFlaskIntegration(WsgiTestBase):
    def setUp(self):
        super().setUp()

        self.app = Flask(__name__)

        def hello_endpoint(helloid):
            if helloid == 500:
                raise ValueError(":-(")
            return "Hello: " + str(helloid)

        self.app.route("/hello/<int:helloid>")(hello_endpoint)

        otel_flask.instrument_app(self.app)
        self.client = Client(self.app, BaseResponse)

    def test_simple(self):
        expected_attrs = {
            "component": "http",
            "http.method": "GET",
            "http.host": "localhost",
            "http.url": "http://localhost/hello/123",
            "http.route": "/hello/<int:helloid>",
            "http.status_code": 200,
            "http.status_text": "OK",
        }
        resp = self.client.get("/hello/123")
        self.assertEqual(200, resp.status_code)
        self.assertEqual([b"Hello: 123"], list(resp.response))
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "hello_endpoint")
        self.assertEqual(span_list[0].kind, trace_api.SpanKind.SERVER)
        self.assertEqual(span_list[0].attributes, expected_attrs)

    def test_404(self):
        expected_attrs = {
            "component": "http",
            "http.method": "POST",
            "http.host": "localhost",
            "http.url": "http://localhost/bye",
            "http.status_code": 404,
            "http.status_text": "NOT FOUND",
        }
        resp = self.client.post("/bye")
        self.assertEqual(404, resp.status_code)
        resp.close()
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "/bye")
        self.assertEqual(span_list[0].kind, trace_api.SpanKind.SERVER)
        self.assertEqual(span_list[0].attributes, expected_attrs)

    def test_internal_error(self):
        expected_attrs = {
            "component": "http",
            "http.method": "GET",
            "http.host": "localhost",
            "http.url": "http://localhost/hello/500",
            "http.route": "/hello/<int:helloid>",
            "http.status_code": 500,
            "http.status_text": "INTERNAL SERVER ERROR",
        }
        resp = self.client.get("/hello/500")
        self.assertEqual(500, resp.status_code)
        resp.close()
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "hello_endpoint")
        self.assertEqual(span_list[0].kind, trace_api.SpanKind.SERVER)
        self.assertEqual(span_list[0].attributes, expected_attrs)


if __name__ == "__main__":
    unittest.main()
