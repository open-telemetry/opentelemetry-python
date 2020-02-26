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
from unittest import mock

import pkg_resources
import requests
import urllib3

import opentelemetry.ext.http_requests
from opentelemetry import trace


class TestRequestsIntegration(unittest.TestCase):

    # TODO: Copy & paste from test_wsgi_middleware
    def setUp(self):
        self.span_attrs = {}
        self.tracer_provider = trace.DefaultTracerProvider()
        self.tracer = trace.DefaultTracer()
        self.get_tracer_patcher = mock.patch.object(
            self.tracer_provider,
            "get_tracer",
            autospec=True,
            spec_set=True,
            return_value=self.tracer,
        )
        self.get_tracer = self.get_tracer_patcher.start()
        self.span_context_manager = mock.MagicMock()
        self.span = mock.create_autospec(trace.Span, spec_set=True)
        self.span_context_manager.__enter__.return_value = self.span

        def setspanattr(key, value):
            self.assertIsInstance(key, str)
            self.span_attrs[key] = value

        self.span.set_attribute = setspanattr
        self.start_span_patcher = mock.patch.object(
            self.tracer,
            "start_as_current_span",
            autospec=True,
            spec_set=True,
            return_value=self.span_context_manager,
        )

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

        self.start_as_current_span = self.start_span_patcher.start()
        self.send = self.send_patcher.start()

        opentelemetry.ext.http_requests.enable(self.tracer_provider)
        distver = pkg_resources.get_distribution(
            "opentelemetry-ext-http-requests"
        ).version
        self.get_tracer.assert_called_with(
            opentelemetry.ext.http_requests.__name__, distver
        )

    def tearDown(self):
        opentelemetry.ext.http_requests.disable()
        self.get_tracer_patcher.stop()
        self.send_patcher.stop()
        self.start_span_patcher.stop()

    def test_basic(self):
        url = "https://www.example.org/foo/bar?x=y#top"
        requests.get(url=url)
        self.assertEqual(1, len(self.send.call_args_list))
        self.tracer.start_as_current_span.assert_called_with(  # pylint:disable=no-member
            "/foo/bar", kind=trace.SpanKind.CLIENT
        )
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
            requests.post(url=url)
        call_args = (
            self.tracer.start_as_current_span.call_args  # pylint:disable=no-member
        )
        self.assertTrue(
            call_args[0][0].startswith("<Unparsable URL"),
            msg=self.tracer.start_as_current_span.call_args,  # pylint:disable=no-member
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
