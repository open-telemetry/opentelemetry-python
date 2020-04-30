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
from unittest.mock import patch

from flask import Flask, request
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from opentelemetry import trace as trace_api
from opentelemetry.configuration import Configuration
from opentelemetry.test.wsgitestutil import WsgiTestBase


def expected_attributes(override_attributes):
    default_attributes = {
        "component": "http",
        "http.method": "GET",
        "http.server_name": "localhost",
        "http.scheme": "http",
        "host.port": 80,
        "http.host": "localhost",
        "http.target": "/",
        "http.flavor": "1.1",
        "http.status_text": "OK",
        "http.status_code": 200,
    }
    for key, val in override_attributes.items():
        default_attributes[key] = val
    return default_attributes


class TestFlaskIntegration(WsgiTestBase):
    def setUp(self):
        # No instrumentation code is here because it is present in the
        # conftest.py file next to this file.
        super().setUp()
        Configuration._instance = None  # pylint:disable=protected-access
        Configuration.__slots__ = []
        self.app = Flask(__name__)

        def hello_endpoint(helloid):
            if helloid == 500:
                raise ValueError(":-(")
            return "Hello: " + str(helloid)

        def excluded_endpoint():
            return "excluded"

        def excluded2_endpoint():
            return "excluded2"

        self.app.route("/hello/<int:helloid>")(hello_endpoint)
        self.app.route("/excluded")(excluded_endpoint)
        self.app.route("/excluded2")(excluded2_endpoint)

        self.client = Client(self.app, BaseResponse)

    def tearDown(self):
        Configuration._instance = None  # pylint:disable=protected-access
        Configuration.__slots__ = []

    def test_only_strings_in_environ(self):
        """
        Some WSGI servers (such as Gunicorn) expect keys in the environ object
        to be strings

        OpenTelemetry should adhere to this convention.
        """
        nonstring_keys = set()

        def assert_environ():
            for key in request.environ:
                if not isinstance(key, str):
                    nonstring_keys.add(key)
            return "hi"

        self.app.route("/assert_environ")(assert_environ)
        self.client.get("/assert_environ")
        self.assertEqual(nonstring_keys, set())

    def test_simple(self):
        expected_attrs = expected_attributes(
            {"http.target": "/hello/123", "http.route": "/hello/<int:helloid>"}
        )
        self.client.get("/hello/123")

        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "hello_endpoint")
        self.assertEqual(span_list[0].kind, trace_api.SpanKind.SERVER)
        self.assertEqual(span_list[0].attributes, expected_attrs)

    def test_404(self):
        expected_attrs = expected_attributes(
            {
                "http.method": "POST",
                "http.target": "/bye",
                "http.status_text": "NOT FOUND",
                "http.status_code": 404,
            }
        )

        resp = self.client.post("/bye")
        self.assertEqual(404, resp.status_code)
        resp.close()
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "/bye")
        self.assertEqual(span_list[0].kind, trace_api.SpanKind.SERVER)
        self.assertEqual(span_list[0].attributes, expected_attrs)

    def test_internal_error(self):
        expected_attrs = expected_attributes(
            {
                "http.target": "/hello/500",
                "http.route": "/hello/<int:helloid>",
                "http.status_text": "INTERNAL SERVER ERROR",
                "http.status_code": 500,
            }
        )
        resp = self.client.get("/hello/500")
        self.assertEqual(500, resp.status_code)
        resp.close()
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "hello_endpoint")
        self.assertEqual(span_list[0].kind, trace_api.SpanKind.SERVER)
        self.assertEqual(span_list[0].attributes, expected_attrs)

    @patch.dict(
        "os.environ",  # type: ignore
        {
            "OPENTELEMETRY_PYTHON_FLASK_EXCLUDED_HOSTS": "http://localhost/excluded",
            "OPENTELEMETRY_PYTHON_FLASK_EXCLUDED_PATHS": "excluded2",
        },
    )
    def test_excluded_path(self):
        self.client.get("/hello/123")
        self.client.get("/excluded")
        self.client.get("/excluded2")
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "hello_endpoint")


if __name__ == "__main__":
    unittest.main()
