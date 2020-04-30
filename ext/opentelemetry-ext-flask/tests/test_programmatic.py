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

from flask import Flask
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from opentelemetry import trace as trace_api
from opentelemetry.ext.flask import FlaskInstrumentor
from opentelemetry.test.wsgitestutil import WsgiTestBase

# pylint: disable=import-error
from .base_test import InstrumentationTest, expected_attributes


class TestProgrammatic(WsgiTestBase, InstrumentationTest):
    def setUp(self):
        # No instrumentation code is here because it is present in the
        # conftest.py file next to this file.
        super().setUp()

        self.app = Flask(__name__)

        FlaskInstrumentor().instrument_app(self.app)

        def hello_endpoint(helloid):
            if helloid == 500:
                raise ValueError(":-(")
            return "Hello: " + str(helloid)

        self.app.route("/hello/<int:helloid>")(hello_endpoint)

        self.client = Client(self.app, BaseResponse)

    def tearDown(self):
        disable(WARNING)
        FlaskInstrumentor().uninstrument_app(self.app)
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

        FlaskInstrumentor().uninstrument_app(self.app)

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
