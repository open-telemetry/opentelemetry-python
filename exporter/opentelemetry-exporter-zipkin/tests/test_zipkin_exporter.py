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
import os
import unittest
from unittest.mock import patch

from opentelemetry.configuration import Configuration
from opentelemetry.exporter.zipkin import (
    ZipkinSpanExporter,
    DEFAULT_ENDPOINT,
    DEFAULT_ENCODING,
    DEFAULT_SERVICE_NAME,
)
from opentelemetry.exporter.zipkin.encoder import Encoding
from opentelemetry.exporter.zipkin.encoder.v2.json import JsonV2Encoder
from opentelemetry.exporter.zipkin.encoder.v2.protobuf import ProtobufEncoder
from opentelemetry.exporter.zipkin.endpoint import Endpoint
from opentelemetry.exporter.zipkin.sender.http import HttpSender
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
        if "OTEL_EXPORTER_ZIPKIN_ENCODING" in os.environ:
            del os.environ["OTEL_EXPORTER_ZIPKIN_ENCODING"]
        Configuration()._reset()  # pylint: disable=protected-access

    def test_constructor_default(self):
        exporter = ZipkinSpanExporter()
        self.assertIsInstance(exporter.encoder, JsonV2Encoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name, DEFAULT_SERVICE_NAME
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertIsInstance(exporter.sender, HttpSender)
        self.assertEqual(exporter.sender.endpoint, DEFAULT_ENDPOINT)
        self.assertEqual(exporter.sender.encoding, DEFAULT_ENCODING)

    def test_constructor_env_vars(self):
        os_service_name = "os-env-service-name"
        os_endpoint = "https://foo:9911/path"
        os_encoding = Encoding.V2_PROTOBUF

        os.environ["OTEL_EXPORTER_ZIPKIN_SERVICE_NAME"] = os_service_name
        os.environ["OTEL_EXPORTER_ZIPKIN_ENDPOINT"] = os_endpoint
        os.environ["OTEL_EXPORTER_ZIPKIN_ENCODING"] = os_encoding.value

        exporter = ZipkinSpanExporter()

        self.assertIsInstance(exporter.encoder, ProtobufEncoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name, os_service_name
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertIsInstance(exporter.sender, HttpSender)
        self.assertEqual(exporter.sender.endpoint, os_endpoint)
        self.assertEqual(exporter.sender.encoding, os_encoding)

    def test_constructor_service(self):
        service_name = "my-service-name"
        exporter = ZipkinSpanExporter(service_name)

        self.assertIsInstance(exporter.encoder, JsonV2Encoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name, service_name
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertIsInstance(exporter.sender, HttpSender)
        self.assertEqual(exporter.sender.endpoint, DEFAULT_ENDPOINT)
        self.assertEqual(exporter.sender.encoding, DEFAULT_ENCODING)

    def test_constructor_service_endpoint_encoding(self):
        """Test the constructor for the common usage of providing the
        service_name, endpoint and encoding arguments."""
        service_name = "my-opentelemetry-zipkin"
        endpoint = "https://opentelemetry.io:15875/myapi/traces?format=zipkin"
        encoding = Encoding.V2_PROTOBUF

        exporter = ZipkinSpanExporter(service_name, endpoint, encoding)

        self.assertIsInstance(exporter.encoder, ProtobufEncoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name, service_name
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertIsInstance(exporter.sender, HttpSender)
        self.assertEqual(exporter.sender.endpoint, endpoint)
        self.assertEqual(exporter.sender.encoding, encoding)

    def test_constructor_sender_encoder(self):
        """Test the constructor for the more advanced use case of providing
        a sender and encoder."""
        service_name = "my-test-service"
        endpoint = "https://opentelemetry.io:15875/myapi/traces?format=zipkin"
        encoding = Encoding.V2_PROTOBUF
        exporter = ZipkinSpanExporter(
            encoder=ProtobufEncoder(Endpoint(service_name)),
            sender=HttpSender(endpoint, encoding),
        )

        self.assertIsInstance(exporter.encoder, ProtobufEncoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name, service_name
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertIsInstance(exporter.sender, HttpSender)
        self.assertEqual(exporter.sender.endpoint, endpoint)
        self.assertEqual(exporter.sender.encoding, encoding)

    def test_constructor_all_params_and_env_vars(self):
        """Test the scenario where all params are provided and all OS env
        vars are set.

        The result should be that the OS env vars and class defaults are
        superseded by the explicit sender and encoder provided.
        """
        os_endpoint = "https://os.env.param:9911/path"
        os_encoding = Encoding.V1_JSON
        os.environ["OTEL_EXPORTER_ZIPKIN_ENDPOINT"] = os_endpoint
        os.environ["OTEL_EXPORTER_ZIPKIN_ENCODING"] = os_encoding.value

        exporter_param_service_name = "exporter-param-service-name"
        exporter_param_endpoint = "https://constructor.param:9911/path"
        exporter_param_encoding = Encoding.V1_JSON

        encoder_param_service_name = "encoder-param-service-name"
        sender_param_encoding = Encoding.V2_PROTOBUF
        sender_param_endpoint = "https://sender.param:9911/path"

        exporter = ZipkinSpanExporter(
            service_name=exporter_param_service_name,
            endpoint=exporter_param_endpoint,
            encoding=exporter_param_encoding,
            encoder=ProtobufEncoder(Endpoint(encoder_param_service_name)),
            sender=HttpSender(sender_param_endpoint, sender_param_encoding),
        )

        self.assertIsInstance(exporter.encoder, ProtobufEncoder)
        self.assertEqual(
            exporter.encoder.local_endpoint.service_name,
            encoder_param_service_name,
        )
        self.assertEqual(exporter.encoder.local_endpoint.ipv4, None)
        self.assertEqual(exporter.encoder.local_endpoint.ipv6, None)
        self.assertEqual(exporter.encoder.local_endpoint.port, None)
        self.assertIsInstance(exporter.sender, HttpSender)
        self.assertEqual(exporter.sender.endpoint, sender_param_endpoint)
        self.assertEqual(exporter.sender.encoding, sender_param_encoding)

    @patch("requests.post")
    def test_invalid_response(self, mock_post):
        mock_post.return_value = MockResponse(404)
        spans = []
        exporter = ZipkinSpanExporter("test-service")
        status = exporter.export(spans)
        self.assertEqual(SpanExportResult.FAILURE, status)
