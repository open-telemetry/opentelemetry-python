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

from flask import Flask

from opentelemetry import trace
from opentelemetry.configuration import Configuration
from opentelemetry.ext.flask import FlaskInstrumentor
from opentelemetry.test.test_base import TestBase
from opentelemetry.test.wsgitestutil import WsgiTestBase

# pylint: disable=import-error
from .base_test import InstrumentationTest, expected_attributes


class TestProgrammatic(InstrumentationTest, TestBase, WsgiTestBase):
    def setUp(self):
        super().setUp()

        Configuration._instance = None  # pylint: disable=protected-access
        Configuration.__slots__ = []  # pylint: disable=protected-access
        self.app = Flask(__name__)

        FlaskInstrumentor().instrument_app(self.app)

        self._common_initialization()

    def tearDown(self):
        super().tearDown()
        with self.disable_logging():
            FlaskInstrumentor().uninstrument_app(self.app)

    def test_uninstrument(self):
        expected_attrs = expected_attributes(
            {"http.target": "/hello/123", "http.route": "/hello/<int:helloid>"}
        )
        resp = self.client.get("/hello/123")
        self.assertEqual(200, resp.status_code)
        self.assertEqual([b"Hello: 123"], list(resp.response))
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "_hello_endpoint")
        self.assertEqual(span_list[0].kind, trace.SpanKind.SERVER)
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
        self.assertEqual(span_list[0].name, "_hello_endpoint")
        self.assertEqual(span_list[0].kind, trace.SpanKind.SERVER)
        self.assertEqual(span_list[0].attributes, expected_attrs)
