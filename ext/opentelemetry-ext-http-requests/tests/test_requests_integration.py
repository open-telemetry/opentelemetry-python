import unittest
from unittest import mock

import requests
import opentelemetry.ext.http_requests
from opentelemetry import trace

class TestRequestsIntegration(unittest.TestCase):

    # TODO: Copy & paste from test_wsgi_middleware
    def setUp(self):
        self.span_attrs = {}
        self.tracer = trace.tracer()
        self.span_context_manager = mock.MagicMock()
        self.span = mock.create_autospec(
            trace.Span, spec_set=True
        )
        self.span_context_manager.__enter__.return_value = self.span

        def setspanattr(key, value):
            self.assertIsInstance(key, str)
            self.span_attrs[key] = value

        self.span.set_attribute = setspanattr
        self.patcher = mock.patch.object(
            self.tracer,
            "start_span",
            autospec=True,
            spec_set=True,
            return_value=self.span_context_manager
        )
        self.start_span = self.patcher.start()

        mocked_response = mock.MagicMock()
        mocked_response.status_code = 200
        mocked_response.reason = "Roger that!"
        send = mock.patch.object(
            requests.Session, "send", autospec=True, spec_set=True,
            return_value=mocked_response)
        self.send = send.start()

    def tearDown(self):
        self.patcher.stop()

    def test_basic(self):
        try:

            opentelemetry.ext.http_requests.enable(self.tracer)
            url = "https://www.example.org/foo/bar?x=y#top"
            _response = requests.get(url=url)
            self.send.assert_called()
            self.tracer.start_span.assert_called_with('/foo/bar')
            self.span_context_manager.__enter__.assert_called()
            self.span_context_manager.__exit__.assert_called()
            self.assertEqual(self.span_attrs, {
                "component": "http",
                "http.method": "GET",
                "http.url": url,
                "http.status_code": 200,
                "http.status_text": "Roger that!"
            })
        finally:
            opentelemetry.ext.http_requests.disable()
