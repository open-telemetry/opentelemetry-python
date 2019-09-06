import sys
import unittest
from unittest import mock

import requests
import urllib3

import opentelemetry.ext.http_requests
from opentelemetry import trace
from opentelemetry import propagator
from opentelemetry.context import Context


class TestRequestsIntegration(unittest.TestCase):

    # TODO: Copy & paste from test_wsgi_middleware
    def setUp(self):
        propagator.set_propagator(propagator.Propagator(Context, None, None))
        self.span_attrs = {}
        self.tracer = trace.tracer()
        self.span_context_manager = mock.MagicMock()
        self.span = mock.create_autospec(trace.Span, spec_set=True)
        self.span_context_manager.__enter__.return_value = self.span

        def setspanattr(key, value):
            self.assertIsInstance(key, str)
            self.span_attrs[key] = value

        self.span.set_attribute = setspanattr
        self.start_span_patcher = mock.patch.object(
            self.tracer,
            "start_span",
            autospec=True,
            spec_set=True,
            return_value=self.span_context_manager,
        )
        self.start_span = self.start_span_patcher.start()

        mocked_response = requests.models.Response()
        mocked_response.status_code = 200
        mocked_response.reason = "Roger that!"
        self.send_patcher = mock.patch.object(
            requests.Session,
            "send",
            autospec=True,
            spec_set=True,
            return_value=mocked_response,
        )
        self.send = self.send_patcher.start()

        opentelemetry.ext.http_requests.enable(self.tracer)

    def tearDown(self):
        opentelemetry.ext.http_requests.disable()
        self.send_patcher.stop()
        self.start_span_patcher.stop()

    def test_basic(self):
        url = "https://www.example.org/foo/bar?x=y#top"
        _response = requests.get(url=url)
        self.assertEqual(1, len(self.send.call_args_list))
        self.tracer.start_span.assert_called_with("/foo/bar")
        self.span_context_manager.__enter__.assert_called_with()
        self.span_context_manager.__exit__.assert_called_with(None, None, None)
        self.assertEqual(
            self.span_attrs,
            {
                "component": "http",
                "http.method": "GET",
                "http.url": url,
                "http.status_code": 200,
                "http.status_text": "Roger that!",
            },
        )

    def test_invalid_url(self):
        url = "http://[::1/nope"
        exception_type = requests.exceptions.InvalidURL
        if sys.version_info[:2] < (3, 5) and tuple(
            map(int, urllib3.__version__.split(".")[:2])
        ) < (1, 25):
            exception_type = ValueError

        with self.assertRaises(exception_type):
            _response = requests.post(url=url)
        self.assertTrue(
            self.tracer.start_span.call_args[0][0].startswith(
                "<Unparsable URL"
            ),
            msg=self.tracer.start_span.call_args,
        )
        self.span_context_manager.__enter__.assert_called_with()
        exitspan = self.span_context_manager.__exit__
        self.assertEqual(1, len(exitspan.call_args_list))
        self.assertIs(exception_type, exitspan.call_args[0][0])
        self.assertIsInstance(exitspan.call_args[0][1], exception_type)
        self.assertEqual(
            self.span_attrs,
            {"component": "http", "http.method": "POST", "http.url": url},
        )
