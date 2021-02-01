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

# pylint: disable=too-many-lines
import ipaddress
import os
import unittest
from unittest.mock import patch

from opentelemetry.configuration import Configuration
from opentelemetry.exporter.zipkin import (
    DEFAULT_ENDPOINT,
    DEFAULT_SERVICE_NAME,
    ZipkinSpanExporter,
)
from opentelemetry.exporter.zipkin.encoder import Encoding
from opentelemetry.exporter.zipkin.encoder.v2.json import JsonV2Encoder
from opentelemetry.exporter.zipkin.encoder.v2.protobuf import ProtobufEncoder
from opentelemetry.exporter.zipkin.node_endpoint import NodeEndpoint
from opentelemetry.sdk.trace.export import SpanExportResult


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = status_code


class TestZipkinSpanExporter(unittest.TestCase):
    def tearDown(self):
        if "OTEL_EXPORTER_ZIPKIN_SERVICE_NAME" in os.environ:
            del os.environ["OTEL_EXPORTER_ZIPKIN_SERVICE_NAME"]
        if "OTEL_EXPORTER_ZIPKIN_ENDPOINT" in os.environ:
            del os.environ["OTEL_EXPORTER_ZIPKIN_ENDPOINT"]
        Configuration()._reset()  # pylint: disable=protected-access

    def test_constructor_default(self):
        exporter = ZipkinSpanExporter()
        self.assertIsInstance(exporter.encoder, JsonV2Encoder)
        self.assertEqual(exporter.endpoint, DEFAULT_ENDPOINT)
        self.assertEqual(
            exporter.local_node.service_name, DEFAULT_SERVICE_NAME
        )
        self.assertEqual(exporter.local_node.ipv4, None)
        self.assertEqual(exporter.local_node.ipv6, None)
        self.assertEqual(exporter.local_node.port, None)

    def test_constructor_env_vars(self):
        os_service_name = "os-env-service-name"
        os_endpoint = "https://foo:9911/path"

        os.environ["OTEL_EXPORTER_ZIPKIN_SERVICE_NAME"] = os_service_name
        os.environ["OTEL_EXPORTER_ZIPKIN_ENDPOINT"] = os_endpoint

        exporter = ZipkinSpanExporter()

        self.assertEqual(exporter.endpoint, os_endpoint)
        self.assertEqual(exporter.local_node.service_name, os_service_name)
        self.assertEqual(exporter.local_node.ipv4, None)
        self.assertEqual(exporter.local_node.ipv6, None)
        self.assertEqual(exporter.local_node.port, None)

    def test_constructor_service(self):
        service_name = "my-service-name"
        exporter = ZipkinSpanExporter(service_name)

        self.assertIsInstance(exporter.encoder, JsonV2Encoder)
        self.assertEqual(exporter.endpoint, DEFAULT_ENDPOINT)
        self.assertEqual(exporter.local_node.service_name, service_name)
        self.assertEqual(exporter.local_node.ipv4, None)
        self.assertEqual(exporter.local_node.ipv6, None)
        self.assertEqual(exporter.local_node.port, None)

    def test_constructor_service_endpoint_encoding(self):
        """Test the constructor for the common usage of providing the
        service_name, endpoint and encoding arguments."""
        service_name = "my-opentelemetry-zipkin"
        endpoint = "https://opentelemetry.io:15875/myapi/traces?format=zipkin"
        encoding = Encoding.V2_PROTOBUF

        exporter = ZipkinSpanExporter(service_name, endpoint, encoding)

        self.assertIsInstance(exporter.encoder, ProtobufEncoder)
        self.assertEqual(exporter.endpoint, endpoint)
        self.assertEqual(exporter.local_node.service_name, service_name)
        self.assertEqual(exporter.local_node.ipv4, None)
        self.assertEqual(exporter.local_node.ipv6, None)
        self.assertEqual(exporter.local_node.port, None)

    def test_constructor_all_params_and_env_vars(self):
        """Test the scenario where all params are provided and all OS env
        vars are set. Explicit params should take precedence.
        """
        os_service_name = "os-env-service-name"
        os_endpoint = "https://os.env.param:9911/path"
        os.environ["OTEL_EXPORTER_ZIPKIN_SERVICE_NAME"] = os_service_name
        os.environ["OTEL_EXPORTER_ZIPKIN_ENDPOINT"] = os_endpoint

        constructor_param_service_name = "exporter-param-service-name"
        constructor_param_endpoint = "https://constructor.param:9911/path"
        constructor_param_encoding = Encoding.V2_PROTOBUF
        local_node_ipv4 = "192.168.0.1"
        local_node_ipv6 = "2001:db8::1000"
        local_node_port = 30301
        max_tag_value_length = 56

        exporter = ZipkinSpanExporter(
            constructor_param_service_name,
            constructor_param_endpoint,
            constructor_param_encoding,
            local_node_ipv4,
            local_node_ipv6,
            local_node_port,
            max_tag_value_length,
        )

        self.assertIsInstance(exporter.encoder, ProtobufEncoder)
        self.assertEqual(exporter.endpoint, constructor_param_endpoint)
        self.assertEqual(
            exporter.local_node.service_name, constructor_param_service_name,
        )
        self.assertEqual(
            exporter.local_node.ipv4, ipaddress.IPv4Address(local_node_ipv4)
        )
        self.assertEqual(
            exporter.local_node.ipv6, ipaddress.IPv6Address(local_node_ipv6)
        )
        self.assertEqual(exporter.local_node.port, local_node_port)

    @patch("requests.post")
    def test_invalid_response(self, mock_post):
        mock_post.return_value = MockResponse(404)
        spans = []
        exporter = ZipkinSpanExporter("test-service")
        status = exporter.export(spans)
        self.assertEqual(SpanExportResult.FAILURE, status)


class TestZipkinNodeEndpoint(unittest.TestCase):
    def test_constructor_default(self):
        service_name = "test-service-name"
        node_endpoint = NodeEndpoint(service_name)
        self.assertEqual(node_endpoint.service_name, service_name)
        self.assertEqual(node_endpoint.ipv4, None)
        self.assertEqual(node_endpoint.ipv6, None)
        self.assertEqual(node_endpoint.port, None)

    def test_constructor_explicits(self):
        service_name = "test-service-name"
        ipv4 = "192.168.0.1"
        ipv6 = "2001:db8::c001"
        port = 414120
        node_endpoint = NodeEndpoint(service_name, ipv4, ipv6, port)
        self.assertEqual(node_endpoint.service_name, service_name)
        self.assertEqual(node_endpoint.ipv4, ipaddress.IPv4Address(ipv4))
        self.assertEqual(node_endpoint.ipv6, ipaddress.IPv6Address(ipv6))
        self.assertEqual(node_endpoint.port, port)

    def test_ipv4_invalid_raises_error(self):
        with self.assertRaises(ValueError):
            NodeEndpoint("service-name", ipv4="invalid-ipv4-address")

    def test_ipv4_passed_ipv6_raises_error(self):
        with self.assertRaises(ValueError):
            NodeEndpoint("service-name", ipv4="2001:db8::c001")

    def test_ipv6_invalid_raises_error(self):
        with self.assertRaises(ValueError):
            NodeEndpoint("service-name", ipv6="invalid-ipv6-address")

    def test_ipv6_passed_ipv4_raises_error(self):
        with self.assertRaises(ValueError):
            NodeEndpoint("service-name", ipv6="192.168.0.1")
