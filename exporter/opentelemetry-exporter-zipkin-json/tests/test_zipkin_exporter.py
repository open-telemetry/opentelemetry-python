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

import ipaddress
import os
import unittest
from unittest.mock import patch

import requests

from opentelemetry import trace
from opentelemetry.exporter.zipkin.encoder import Protocol
from opentelemetry.exporter.zipkin.json import DEFAULT_ENDPOINT, ZipkinExporter
from opentelemetry.exporter.zipkin.json.v2 import JsonV2Encoder
from opentelemetry.exporter.zipkin.node_endpoint import NodeEndpoint
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_ZIPKIN_ENDPOINT,
    OTEL_EXPORTER_ZIPKIN_TIMEOUT,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider, _Span
from opentelemetry.sdk.trace.export import SpanExportResult

TEST_SERVICE_NAME = "test_service"


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = status_code


class TestZipkinExporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        trace.set_tracer_provider(
            TracerProvider(
                resource=Resource({SERVICE_NAME: TEST_SERVICE_NAME})
            )
        )

    def tearDown(self):
        os.environ.pop(OTEL_EXPORTER_ZIPKIN_ENDPOINT, None)
        os.environ.pop(OTEL_EXPORTER_ZIPKIN_TIMEOUT, None)

    def test_constructor_default(self):
        exporter = ZipkinExporter()
        self.assertIsInstance(exporter.encoder, JsonV2Encoder)
        self.assertIsInstance(exporter.session, requests.Session)
        self.assertEqual(exporter.endpoint, DEFAULT_ENDPOINT)
        self.assertEqual(exporter.local_node.service_name, TEST_SERVICE_NAME)
        self.assertEqual(exporter.local_node.ipv4, None)
        self.assertEqual(exporter.local_node.ipv6, None)
        self.assertEqual(exporter.local_node.port, None)

    def test_constructor_env_vars(self):
        os_endpoint = "https://foo:9911/path"
        os.environ[OTEL_EXPORTER_ZIPKIN_ENDPOINT] = os_endpoint
        os.environ[OTEL_EXPORTER_ZIPKIN_TIMEOUT] = "15"

        exporter = ZipkinExporter()

        self.assertEqual(exporter.endpoint, os_endpoint)
        self.assertEqual(exporter.local_node.service_name, TEST_SERVICE_NAME)
        self.assertEqual(exporter.local_node.ipv4, None)
        self.assertEqual(exporter.local_node.ipv6, None)
        self.assertEqual(exporter.local_node.port, None)
        self.assertEqual(exporter.timeout, 15)

    def test_constructor_protocol_endpoint(self):
        """Test the constructor for the common usage of providing the
        protocol and endpoint arguments."""
        endpoint = "https://opentelemetry.io:15875/myapi/traces?format=zipkin"

        exporter = ZipkinExporter(endpoint=endpoint)

        self.assertIsInstance(exporter.encoder, JsonV2Encoder)
        self.assertIsInstance(exporter.session, requests.Session)
        self.assertEqual(exporter.endpoint, endpoint)
        self.assertEqual(exporter.local_node.service_name, TEST_SERVICE_NAME)
        self.assertEqual(exporter.local_node.ipv4, None)
        self.assertEqual(exporter.local_node.ipv6, None)
        self.assertEqual(exporter.local_node.port, None)

    def test_constructor_all_params_and_env_vars(self):
        """Test the scenario where all params are provided and all OS env
        vars are set. Explicit params should take precedence.
        """
        os_endpoint = "https://os.env.param:9911/path"
        os.environ[OTEL_EXPORTER_ZIPKIN_ENDPOINT] = os_endpoint
        os.environ[OTEL_EXPORTER_ZIPKIN_TIMEOUT] = "15"

        constructor_param_version = Protocol.V2
        constructor_param_endpoint = "https://constructor.param:9911/path"
        local_node_ipv4 = "192.168.0.1"
        local_node_ipv6 = "2001:db8::1000"
        local_node_port = 30301
        max_tag_value_length = 56
        timeout_param = 20
        session_param = requests.Session()

        exporter = ZipkinExporter(
            constructor_param_version,
            constructor_param_endpoint,
            local_node_ipv4,
            local_node_ipv6,
            local_node_port,
            max_tag_value_length,
            timeout_param,
            session_param,
        )

        self.assertIsInstance(exporter.encoder, JsonV2Encoder)
        self.assertIsInstance(exporter.session, requests.Session)
        self.assertEqual(exporter.endpoint, constructor_param_endpoint)
        self.assertEqual(exporter.local_node.service_name, TEST_SERVICE_NAME)
        self.assertEqual(
            exporter.local_node.ipv4, ipaddress.IPv4Address(local_node_ipv4)
        )
        self.assertEqual(
            exporter.local_node.ipv6, ipaddress.IPv6Address(local_node_ipv6)
        )
        self.assertEqual(exporter.local_node.port, local_node_port)
        # Assert timeout passed in constructor is prioritized over env
        # when both are set.
        self.assertEqual(exporter.timeout, 20)

    @patch("requests.Session.post")
    def test_export_success(self, mock_post):
        mock_post.return_value = MockResponse(200)
        spans = []
        exporter = ZipkinExporter()
        status = exporter.export(spans)
        self.assertEqual(SpanExportResult.SUCCESS, status)

    @patch("requests.Session.post")
    def test_export_invalid_response(self, mock_post):
        mock_post.return_value = MockResponse(404)
        spans = []
        exporter = ZipkinExporter()
        status = exporter.export(spans)
        self.assertEqual(SpanExportResult.FAILURE, status)

    @patch("requests.Session.post")
    def test_export_span_service_name(self, mock_post):
        mock_post.return_value = MockResponse(200)
        resource = Resource.create({SERVICE_NAME: "test"})
        context = trace.SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000DEADBEF0,
            is_remote=False,
        )
        span = _Span("test_span", context=context, resource=resource)
        span.start()
        span.end()
        exporter = ZipkinExporter()
        exporter.export([span])
        self.assertEqual(exporter.local_node.service_name, "test")

    @patch("requests.Session.post")
    def test_export_shutdown(self, mock_post):
        mock_post.return_value = MockResponse(200)
        spans = []
        exporter = ZipkinExporter()
        status = exporter.export(spans)
        self.assertEqual(SpanExportResult.SUCCESS, status)

        exporter.shutdown()
        # Any call to .export() post shutdown should return failure
        status = exporter.export(spans)
        self.assertEqual(SpanExportResult.FAILURE, status)

    @patch("requests.Session.post")
    def test_export_timeout(self, mock_post):
        mock_post.return_value = MockResponse(200)
        spans = []
        exporter = ZipkinExporter(timeout=2)
        status = exporter.export(spans)
        self.assertEqual(SpanExportResult.SUCCESS, status)
        mock_post.assert_called_with(
            url="http://localhost:9411/api/v2/spans", data="[]", timeout=2
        )


class TestZipkinNodeEndpoint(unittest.TestCase):
    def test_constructor_default(self):
        node_endpoint = NodeEndpoint()
        self.assertEqual(node_endpoint.ipv4, None)
        self.assertEqual(node_endpoint.ipv6, None)
        self.assertEqual(node_endpoint.port, None)
        self.assertEqual(node_endpoint.service_name, TEST_SERVICE_NAME)

    def test_constructor_explicits(self):
        ipv4 = "192.168.0.1"
        ipv6 = "2001:db8::c001"
        port = 414120
        node_endpoint = NodeEndpoint(ipv4, ipv6, port)
        self.assertEqual(node_endpoint.ipv4, ipaddress.IPv4Address(ipv4))
        self.assertEqual(node_endpoint.ipv6, ipaddress.IPv6Address(ipv6))
        self.assertEqual(node_endpoint.port, port)
        self.assertEqual(node_endpoint.service_name, TEST_SERVICE_NAME)

    def test_ipv4_invalid_raises_error(self):
        with self.assertRaises(ValueError):
            NodeEndpoint(ipv4="invalid-ipv4-address")

    def test_ipv4_passed_ipv6_raises_error(self):
        with self.assertRaises(ValueError):
            NodeEndpoint(ipv4="2001:db8::c001")

    def test_ipv6_invalid_raises_error(self):
        with self.assertRaises(ValueError):
            NodeEndpoint(ipv6="invalid-ipv6-address")

    def test_ipv6_passed_ipv4_raises_error(self):
        with self.assertRaises(ValueError):
            NodeEndpoint(ipv6="192.168.0.1")
