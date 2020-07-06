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

from unittest.mock import patch

from pyramid.config import Configurator

from opentelemetry import trace
from opentelemetry.ext.pyramid import PyramidInstrumentor
from opentelemetry.test.test_base import TestBase
from opentelemetry.test.wsgitestutil import WsgiTestBase

# pylint: disable=import-error
from .pyramid_base_test import InstrumentationTest


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


class TestProgrammatic(InstrumentationTest, TestBase, WsgiTestBase):
    def setUp(self):
        super().setUp()
        config = Configurator()
        PyramidInstrumentor().instrument_config(config)

        self.config = config

        self._common_initialization(self.config)

    def tearDown(self):
        super().tearDown()
        with self.disable_logging():
            PyramidInstrumentor().uninstrument_config(self.config)

    def test_uninstrument(self):
        resp = self.client.get("/hello/123")
        self.assertEqual(200, resp.status_code)
        self.assertEqual([b"Hello: 123"], list(resp.response))
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)

        PyramidInstrumentor().uninstrument_config(self.config)
        # Need to remake the WSGI app export
        self._common_initialization(self.config)

        resp = self.client.get("/hello/123")
        self.assertEqual(200, resp.status_code)
        self.assertEqual([b"Hello: 123"], list(resp.response))
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)

    def test_simple(self):
        expected_attrs = expected_attributes(
            {"http.target": "/hello/123", "http.route": "/hello/{helloid}"}
        )
        self.client.get("/hello/123")
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "/hello/{helloid}")
        self.assertEqual(span_list[0].kind, trace.SpanKind.SERVER)
        self.assertEqual(span_list[0].attributes, expected_attrs)

    def test_404(self):
        expected_attrs = expected_attributes(
            {
                "http.method": "POST",
                "http.target": "/bye",
                "http.status_text": "Not Found",
                "http.status_code": 404,
            }
        )

        resp = self.client.post("/bye")
        self.assertEqual(404, resp.status_code)
        resp.close()
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "HTTP POST")
        self.assertEqual(span_list[0].kind, trace.SpanKind.SERVER)
        self.assertEqual(span_list[0].attributes, expected_attrs)

    def test_internal_error(self):
        expected_attrs = expected_attributes(
            {
                "http.target": "/hello/500",
                "http.route": "/hello/{helloid}",
                "http.status_text": "Internal Server Error",
                "http.status_code": 500,
            }
        )
        resp = self.client.get("/hello/500")
        self.assertEqual(500, resp.status_code)
        resp.close()
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        self.assertEqual(span_list[0].name, "/hello/{helloid}")
        self.assertEqual(span_list[0].kind, trace.SpanKind.SERVER)
        self.assertEqual(span_list[0].attributes, expected_attrs)

    def test_tween_list(self):
        tween_list = "opentelemetry.ext.pyramid.trace_tween_factory\npyramid.tweens.excview_tween_factory"
        config = Configurator(settings={"pyramid.tweens": tween_list})
        PyramidInstrumentor().instrument_config(config)
        self._common_initialization(config)

        resp = self.client.get("/hello/123")
        self.assertEqual(200, resp.status_code)
        self.assertEqual([b"Hello: 123"], list(resp.response))
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)

        PyramidInstrumentor().uninstrument_config(config)
        # Need to remake the WSGI app export
        self._common_initialization(config)

        resp = self.client.get("/hello/123")
        self.assertEqual(200, resp.status_code)
        self.assertEqual([b"Hello: 123"], list(resp.response))
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)

    @patch("opentelemetry.ext.pyramid.callbacks._logger")
    def test_warnings(self, mock_logger):
        tween_list = "pyramid.tweens.excview_tween_factory"
        config = Configurator(settings={"pyramid.tweens": tween_list})
        PyramidInstrumentor().instrument_config(config)
        self._common_initialization(config)

        self.client.get("/hello/123")
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 0)
        self.assertEqual(mock_logger.warning.called, True)

        mock_logger.warning.called = False

        tween_list = "opentelemetry.ext.pyramid.trace_tween_factory"
        config = Configurator(settings={"pyramid.tweens": tween_list})
        self._common_initialization(config)

        self.client.get("/hello/123")
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 0)
        self.assertEqual(mock_logger.warning.called, True)

    @patch(
        "opentelemetry.ext.pyramid.callbacks._excluded_hosts",
        ["http://localhost/excluded_arg/123"],
    )
    @patch(
        "opentelemetry.ext.pyramid.callbacks._excluded_paths",
        ["excluded_noarg"],
    )
    def test_exclude_lists(self):
        self.client.get("/excluded_arg/123")
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 0)

        self.client.get("/excluded_arg/125")
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)

        self.client.get("/excluded_noarg")
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)

        self.client.get("/excluded_noarg2")
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
