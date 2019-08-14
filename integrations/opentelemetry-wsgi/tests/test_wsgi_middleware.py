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
import io
import unittest
import unittest.mock as mock
import wsgiref.util as wsgiref_util
from opentelemetry_wsgi import OpenTelemetryMiddleware
from opentelemetry import trace as trace_api


class Response:
    def __init__(self):
        self.iter = iter([b"*"])

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.iter)


def simple_wsgi(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"*"]


def iter_wsgi(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return Response()


def error_wsgi(environ, start_response):
    try:
        raise ValueError
    except ValueError:
        exc_info = sys.exc_info()
    start_response("200 OK", [("Content-Type", "text/plain")], exc_info)
    exc_info = None
    return [b"*"]


class TestWsgiMiddleware(unittest.TestCase):
    def setUp(self):
        tracer = trace_api.tracer()
        self.span_context_manager = mock.MagicMock()
        self.span_context_manager.__enter__.return_value = mock.create_autospec(
            trace_api.Span, spec_set=True
        )
        self.patcher = mock.patch.object(
            tracer,
            "start_span",
            autospec=True,
            spec_set=True,
            return_value=self.span_context_manager,
        )
        self.start_span = self.patcher.start()

        self.write_buffer = io.BytesIO()
        self.write = self.write_buffer.write

        self.environ = {}
        wsgiref_util.setup_testing_defaults(self.environ)

        self.status = None
        self.response_headers = None
        self.exc_info = None

    def tearDown(self):
        self.patcher.stop()

    def start_response(self, status, response_headers, exc_info=None):
        # The span should have started already
        self.span_context_manager.__enter__.assert_called()

        self.status = status
        self.response_headers = response_headers
        self.exc_info = exc_info
        return self.write

    def validate_response(self, response, error=None):
        while True:
            try:
                value = next(response)
                self.span_context_manager.__exit__.assert_not_called()
                self.assertEqual(value, b"*")
            except StopIteration:
                self.span_context_manager.__exit__.assert_called()
                break

        self.assertEqual(self.status, "200 OK")
        self.assertEqual(self.response_headers, [("Content-Type", "text/plain")])
        if error:
            self.assertIs(self.exc_info[0], error)
            self.assertIsInstance(self.exc_info[1], error)
            self.assertIsNotNone(self.exc_info[2])
        else:
            self.assertIsNone(self.exc_info)

        # Verify that start_span has been called
        self.start_span.assert_called_once_with("[GET]/")

    def test_basic_wsgi_call(self):
        app = OpenTelemetryMiddleware(simple_wsgi)
        response = app(self.environ, self.start_response)
        self.validate_response(response)

    def test_wsgi_iterable(self):
        app = OpenTelemetryMiddleware(iter_wsgi)
        response = app(self.environ, self.start_response)
        # Verify that start_response has not been called yet
        self.assertIsNone(self.status)
        self.validate_response(response)

    def test_wsgi_exc_info(self):
        app = OpenTelemetryMiddleware(error_wsgi)
        response = app(self.environ, self.start_response)
        self.validate_response(response, error=ValueError)


if __name__ == "__main__":
    unittest.main()
