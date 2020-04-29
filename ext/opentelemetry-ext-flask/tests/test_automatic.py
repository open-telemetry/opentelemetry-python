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

from logging import NOTSET, WARNING, disable
from unittest import main

# This is used instead of from flask import Flask, request because if not then
# FlaskInstrumentor().instrument() would need to be called before importing
# Flask. This is just an intrinsic limitation due the fact that we are testing
# the instrumentor in a way that mimics how it would be called with the
# opentelemetry-auto-instrumentation command. This does not mean that the
# instrumentor should be used in this way in end user applications. For those
# cases, FlaskInstrumentor.instrument(app=app) should be used.
import flask
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from opentelemetry import trace as trace_api
from opentelemetry.ext.flask import FlaskInstrumentor
from opentelemetry.test.wsgitestutil import WsgiTestBase

from .base_test import InstrumentationTest, expected_attributes


class TestAutomatic(WsgiTestBase, InstrumentationTest):
    def setUp(self):
        super().setUp()

        FlaskInstrumentor().instrument()

        self.app = flask.Flask(__name__)

        def hello_endpoint(helloid):
            if helloid == 500:
                raise ValueError(":-(")
            return "Hello: " + str(helloid)

        self.app.route("/hello/<int:helloid>")(hello_endpoint)

        self.client = Client(self.app, BaseResponse)

    def tearDown(self):
        disable(WARNING)
        FlaskInstrumentor().uninstrument()
        disable(NOTSET)

    def test_uninstrument(self):
        expected_attrs = expected_attributes(
            {"http.target": "/hello/123", "http.route": "/hello/<int:helloid>"}
        )
        resp = self.client.get("/hello/123")
        self.assertEqual(200, resp.status_code)
        self.assertEqual([b"Hello: 123"], list(resp.response))
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "hello_endpoint")
        self.assertEqual(span_list[0].kind, trace_api.SpanKind.SERVER)
        self.assertEqual(span_list[0].attributes, expected_attrs)

        FlaskInstrumentor().uninstrument()

        expected_attrs = expected_attributes(
            {"http.target": "/hello/123", "http.route": "/hello/<int:helloid>"}
        )
        resp = self.client.get("/hello/123")
        self.assertEqual(200, resp.status_code)
        self.assertEqual([b"Hello: 123"], list(resp.response))
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "hello_endpoint")
        self.assertEqual(span_list[0].kind, trace_api.SpanKind.SERVER)
        self.assertEqual(span_list[0].attributes, expected_attrs)


if __name__ == "__main__":
    main()
