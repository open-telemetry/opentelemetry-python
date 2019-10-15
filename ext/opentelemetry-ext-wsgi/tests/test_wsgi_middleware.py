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
import wsgiref.util as wsgiref_util
from urllib.parse import urlparse

import opentelemetry.ext.wsgi as otel_wsgi
from opentelemetry import trace as trace_api
from wsgitestutil import WsgiTestBase


class Response:
    def __init__(self):
        self.iter = iter([b"*"])
        self.close_calls = 0

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.iter)

    def close(self):
        self.close_calls += 1


def simple_wsgi(environ, start_response):
    assert isinstance(environ, dict)
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"*"]


def create_iter_wsgi(response):
    def iter_wsgi(environ, start_response):
        assert isinstance(environ, dict)
        start_response("200 OK", [("Content-Type", "text/plain")])
        return response

    return iter_wsgi


def create_gen_wsgi(response):
    def gen_wsgi(environ, start_response):
        result = create_iter_wsgi(response)(environ, start_response)
        yield from result
        getattr(result, "close", lambda: None)()

    return gen_wsgi


def error_wsgi(environ, start_response):
    assert isinstance(environ, dict)
    try:
        raise ValueError
    except ValueError:
        exc_info = sys.exc_info()
    start_response("200 OK", [("Content-Type", "text/plain")], exc_info)
    exc_info = None
    return [b"*"]


class TestWsgiApplication(WsgiTestBase):
    def validate_response(self, response, error=None):
        while True:
            try:
                value = next(response)
                self.assertEqual(0, self.span.end.call_count)
                self.assertEqual(value, b"*")
            except StopIteration:
                self.span.end.assert_called_once_with()
                break

        self.assertEqual(self.status, "200 OK")
        self.assertEqual(
            self.response_headers, [("Content-Type", "text/plain")]
        )
        if error:
            self.assertIs(self.exc_info[0], error)
            self.assertIsInstance(self.exc_info[1], error)
            self.assertIsNotNone(self.exc_info[2])
        else:
            self.assertIsNone(self.exc_info)

        # Verify that start_span has been called
        self.create_span.assert_called_with(
            "/", trace_api.INVALID_SPAN_CONTEXT, kind=trace_api.SpanKind.SERVER
        )
        self.assertEqual(1, self.span.start.call_count)

    def test_basic_wsgi_call(self):
        app = otel_wsgi.OpenTelemetryMiddleware(simple_wsgi)
        response = app(self.environ, self.start_response)
        self.validate_response(response)

    def test_wsgi_iterable(self):
        original_response = Response()
        iter_wsgi = create_iter_wsgi(original_response)
        app = otel_wsgi.OpenTelemetryMiddleware(iter_wsgi)
        response = app(self.environ, self.start_response)
        # Verify that start_response has been called
        self.assertTrue(self.status)
        self.validate_response(response)

        # Verify that close has been called exactly once
        self.assertEqual(1, original_response.close_calls)

    def test_wsgi_generator(self):
        original_response = Response()
        gen_wsgi = create_gen_wsgi(original_response)
        app = otel_wsgi.OpenTelemetryMiddleware(gen_wsgi)
        response = app(self.environ, self.start_response)
        # Verify that start_response has not been called
        self.assertIsNone(self.status)
        self.validate_response(response)

        # Verify that close has been called exactly once
        self.assertEqual(original_response.close_calls, 1)

    def test_wsgi_exc_info(self):
        app = otel_wsgi.OpenTelemetryMiddleware(error_wsgi)
        response = app(self.environ, self.start_response)
        self.validate_response(response, error=ValueError)


class TestWsgiAttributes(unittest.TestCase):
    def setUp(self):
        self.environ = {}
        wsgiref_util.setup_testing_defaults(self.environ)
        self.span = mock.create_autospec(trace_api.Span, spec_set=True)

    def test_request_attributes(self):
        self.environ["QUERY_STRING"] = "foo=bar"

        otel_wsgi.add_request_attributes(self.span, self.environ)

        expected = (
            mock.call("component", "http"),
            mock.call("http.method", "GET"),
            mock.call("http.host", "127.0.0.1"),
            mock.call("http.url", "http://127.0.0.1/?foo=bar"),
        )
        self.assertEqual(self.span.set_attribute.call_count, len(expected))
        self.span.set_attribute.assert_has_calls(expected, any_order=True)

    def validate_url(self, expected_url):
        otel_wsgi.add_request_attributes(self.span, self.environ)
        attrs = {
            args[0][0]: args[0][1]
            for args in self.span.set_attribute.call_args_list
        }
        self.assertIn("http.url", attrs)
        self.assertEqual(attrs["http.url"], expected_url)
        self.assertIn("http.host", attrs)
        self.assertEqual(attrs["http.host"], urlparse(expected_url).netloc)

    def test_request_attributes_with_partial_raw_uri(self):
        self.environ["RAW_URI"] = "/#top"
        self.validate_url("http://127.0.0.1/#top")

    def test_request_attributes_with_partial_raw_uri_and_nonstandard_port(
        self
    ):
        self.environ["RAW_URI"] = "/?"
        del self.environ["HTTP_HOST"]
        self.environ["SERVER_PORT"] = "8080"
        self.validate_url("http://127.0.0.1:8080/?")

    def test_https_uri_port(self):
        del self.environ["HTTP_HOST"]
        self.environ["SERVER_PORT"] = "443"
        self.environ["wsgi.url_scheme"] = "https"
        self.validate_url("https://127.0.0.1/")

        self.environ["SERVER_PORT"] = "8080"
        self.validate_url("https://127.0.0.1:8080/")

        self.environ["SERVER_PORT"] = "80"
        self.validate_url("https://127.0.0.1:80/")

    def test_http_uri_port(self):
        del self.environ["HTTP_HOST"]
        self.environ["SERVER_PORT"] = "80"
        self.environ["wsgi.url_scheme"] = "http"
        self.validate_url("http://127.0.0.1/")

        self.environ["SERVER_PORT"] = "8080"
        self.validate_url("http://127.0.0.1:8080/")

        self.environ["SERVER_PORT"] = "443"
        self.validate_url("http://127.0.0.1:443/")

    def test_request_attributes_with_nonstandard_port_and_no_host(self):
        del self.environ["HTTP_HOST"]
        self.environ["SERVER_PORT"] = "8080"
        self.validate_url("http://127.0.0.1:8080/")

        self.environ["SERVER_PORT"] = "443"
        self.validate_url("http://127.0.0.1:443/")

    def test_request_attributes_with_nonstandard_port(self):
        self.environ["HTTP_HOST"] += ":8080"
        self.validate_url("http://127.0.0.1:8080/")

    def test_request_attributes_with_faux_scheme_relative_raw_uri(self):
        self.environ["RAW_URI"] = "//127.0.0.1/?"
        self.validate_url("http://127.0.0.1//127.0.0.1/?")

    def test_request_attributes_with_pathless_raw_uri(self):
        self.environ["PATH_INFO"] = ""
        self.environ["RAW_URI"] = "http://hello"
        self.environ["HTTP_HOST"] = "hello"
        self.validate_url("http://hello")

    def test_request_attributes_with_full_request_uri(self):
        self.environ["HTTP_HOST"] = "127.0.0.1:8080"
        self.environ["REQUEST_URI"] = "http://127.0.0.1:8080/?foo=bar#top"
        self.validate_url("http://127.0.0.1:8080/?foo=bar#top")

    def test_response_attributes(self):
        otel_wsgi.add_response_attributes(self.span, "404 Not Found", {})
        expected = (
            mock.call("http.status_code", 404),
            mock.call("http.status_text", "Not Found"),
        )
        self.assertEqual(self.span.set_attribute.call_count, len(expected))
        self.span.set_attribute.assert_has_calls(expected, any_order=True)

    def test_response_attributes_invalid_status_code(self):
        otel_wsgi.add_response_attributes(self.span, "Invalid Status Code", {})
        self.assertEqual(self.span.set_attribute.call_count, 1)
        self.span.set_attribute.assert_called_with(
            "http.status_text", "Status Code"
        )


if __name__ == "__main__":
    unittest.main()
