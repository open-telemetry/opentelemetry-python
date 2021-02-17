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

import os
import unittest
from unittest.mock import patch

from opentelemetry.exporter.otlp import (
    DEFAULT_COMPRESSION,
    DEFAULT_ENDPOINT,
    DEFAULT_INSECURE,
    DEFAULT_TIMEOUT,
    OTLPSpanExporter,
)
from opentelemetry.exporter.otlp.encoder.protobuf import ProtobufEncoder
from opentelemetry.exporter.otlp.sender.grpc import GrpcSender
from opentelemetry.exporter.otlp.sender.http import HttpSender
from opentelemetry.exporter.otlp.util import Compression, Protocol
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CERTIFICATE,
    OTEL_EXPORTER_OTLP_COMPRESSION,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_INSECURE,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)

OS_ENV_ENDPOINT = "os.env.base"
OS_ENV_CERTIFICATE = "os/env/base.crt"
OS_ENV_HEADERS = "envHeader1=val1,envHeader2=val2"
OS_ENV_TIMEOUT = "300"


# pylint: disable=protected-access
class TestOTLPSpanExporter(unittest.TestCase):
    def tearDown(self):
        otlp_env_vars = [
            "OTEL_EXPORTER_OTLP_CERTIFICATE",
            "OTEL_EXPORTER_OTLP_COMPRESSION",
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "OTEL_EXPORTER_OTLP_HEADERS",
            "OTEL_EXPORTER_OTLP_INSECURE",
            "OTEL_EXPORTER_OTLP_TIMEOUT",
        ]
        for otlp_env_var in otlp_env_vars:
            if otlp_env_var in os.environ:
                del os.environ[otlp_env_var]

    @patch("opentelemetry.exporter.otlp.sender.grpc.GrpcSender.__init__")
    def test_constructor_default(self, mock_grpc_sender):
        mock_grpc_sender.return_value = None

        exporter = OTLPSpanExporter(Protocol.GRPC)

        self.assertIsInstance(exporter._encoder, ProtobufEncoder)
        self.assertIsInstance(exporter._sender, GrpcSender)

        mock_grpc_sender.assert_called_once_with(
            DEFAULT_ENDPOINT,
            DEFAULT_INSECURE,
            None,
            None,
            DEFAULT_TIMEOUT,
            DEFAULT_COMPRESSION,
        )

    @patch("opentelemetry.exporter.otlp.sender.grpc.GrpcSender.__init__")
    def test_constructor_grpc_args(self, mock_grpc_sender):
        mock_grpc_sender.return_value = None

        exporter = OTLPSpanExporter(
            protocol=Protocol.GRPC,
            endpoint="test.endpoint.com:46484",
            insecure=False,
            certificate_file="path/to/service.crt",
            headers={"argHeader1": "value1", "argHeader2": "value2"},
            timeout=2,
            compression=Compression.GZIP,
        )

        self.assertIsInstance(exporter._encoder, ProtobufEncoder)
        self.assertIsInstance(exporter._sender, GrpcSender)

        mock_grpc_sender.assert_called_once_with(
            "test.endpoint.com:46484",
            False,
            "path/to/service.crt",
            {"argHeader1": "value1", "argHeader2": "value2"},
            2,
            Compression.GZIP,
        )

    @patch("opentelemetry.exporter.otlp.sender.grpc.GrpcSender.__init__")
    def test_constructor_grpc_args_override_env_vars(self, mock_grpc_sender):
        mock_grpc_sender.return_value = None

        os.environ[OTEL_EXPORTER_OTLP_CERTIFICATE] = OS_ENV_CERTIFICATE
        os.environ[OTEL_EXPORTER_OTLP_COMPRESSION] = Compression.DEFLATE.value
        os.environ[OTEL_EXPORTER_OTLP_ENDPOINT] = OS_ENV_ENDPOINT
        os.environ[OTEL_EXPORTER_OTLP_HEADERS] = OS_ENV_HEADERS
        os.environ[OTEL_EXPORTER_OTLP_INSECURE] = "true"
        os.environ[OTEL_EXPORTER_OTLP_TIMEOUT] = OS_ENV_TIMEOUT

        exporter = OTLPSpanExporter(
            protocol=Protocol.GRPC,
            endpoint="test.endpoint.com:46484",
            insecure=False,
            certificate_file="path/to/service.crt",
            headers={"argHeader1": "value1", "argHeader2": "value2"},
            timeout=2,
            compression=Compression.GZIP,
        )

        self.assertIsInstance(exporter._encoder, ProtobufEncoder)
        self.assertIsInstance(exporter._sender, GrpcSender)

        mock_grpc_sender.assert_called_once_with(
            "test.endpoint.com:46484",
            False,
            "path/to/service.crt",
            {"argHeader1": "value1", "argHeader2": "value2"},
            2,
            Compression.GZIP,
        )

    @patch("opentelemetry.exporter.otlp.sender.grpc.GrpcSender.__init__")
    def test_constructor_grpc_env_vars(self, mock_grpc_sender):
        mock_grpc_sender.return_value = None

        os.environ[OTEL_EXPORTER_OTLP_CERTIFICATE] = OS_ENV_CERTIFICATE
        os.environ[OTEL_EXPORTER_OTLP_COMPRESSION] = Compression.GZIP.value
        os.environ[OTEL_EXPORTER_OTLP_ENDPOINT] = OS_ENV_ENDPOINT
        os.environ[OTEL_EXPORTER_OTLP_HEADERS] = OS_ENV_HEADERS
        os.environ[OTEL_EXPORTER_OTLP_INSECURE] = "true"
        os.environ[OTEL_EXPORTER_OTLP_TIMEOUT] = OS_ENV_TIMEOUT

        exporter = OTLPSpanExporter(Protocol.GRPC)

        self.assertIsInstance(exporter._encoder, ProtobufEncoder)
        self.assertIsInstance(exporter._sender, GrpcSender)

        mock_grpc_sender.assert_called_once_with(
            OS_ENV_ENDPOINT,
            True,
            None,
            {"envHeader1": "val1", "envHeader2": "val2"},
            int(OS_ENV_TIMEOUT),
            Compression.GZIP,
        )

    @patch("opentelemetry.exporter.otlp.sender.http.HttpSender.__init__")
    def test_constructor_http_args(self, mock_http_sender):
        mock_http_sender.return_value = None

        exporter = OTLPSpanExporter(
            protocol=Protocol.HTTP_PROTOBUF,
            endpoint="test.endpoint.com:46484",
            insecure=False,
            certificate_file="path/to/service.crt",
            headers="testHeader1=value1,testHeader2=value2",
            timeout=2,
            compression=Compression.GZIP,
        )

        self.assertIsInstance(exporter._encoder, ProtobufEncoder)
        self.assertIsInstance(exporter._sender, HttpSender)

        mock_http_sender.assert_called_once_with(
            "test.endpoint.com:46484",
            False,
            "path/to/service.crt",
            {"testHeader1": "value1", "testHeader2": "value2"},
            2,
            Compression.GZIP,
        )

    @patch("opentelemetry.exporter.otlp.sender.http.HttpSender.__init__")
    def test_constructor_span_http_args_override_env(self, mock_http_sender):
        mock_http_sender.return_value = None

        os.environ[OTEL_EXPORTER_OTLP_CERTIFICATE] = OS_ENV_CERTIFICATE
        os.environ[OTEL_EXPORTER_OTLP_COMPRESSION] = Compression.DEFLATE.value
        os.environ[OTEL_EXPORTER_OTLP_ENDPOINT] = OS_ENV_ENDPOINT
        os.environ[OTEL_EXPORTER_OTLP_HEADERS] = OS_ENV_HEADERS
        os.environ[OTEL_EXPORTER_OTLP_INSECURE] = "true"
        os.environ[OTEL_EXPORTER_OTLP_TIMEOUT] = OS_ENV_TIMEOUT

        exporter = OTLPSpanExporter(
            protocol=Protocol.HTTP_PROTOBUF,
            endpoint="test.endpoint.com:46484",
            insecure=False,
            certificate_file="path/to/service.crt",
            headers="testHeader1=value1,testHeader2=value2",
            timeout=2,
            compression=Compression.GZIP,
        )

        self.assertIsInstance(exporter._encoder, ProtobufEncoder)
        self.assertIsInstance(exporter._sender, HttpSender)

        mock_http_sender.assert_called_once_with(
            "test.endpoint.com:46484",
            False,
            "path/to/service.crt",
            {"testHeader1": "value1", "testHeader2": "value2"},
            2,
            Compression.GZIP,
        )

    @patch("opentelemetry.exporter.otlp.sender.http.HttpSender.__init__")
    def test_constructor_span_http_env_vars(self, mock_http_sender):
        mock_http_sender.return_value = None

        os.environ[OTEL_EXPORTER_OTLP_CERTIFICATE] = OS_ENV_CERTIFICATE
        os.environ[OTEL_EXPORTER_OTLP_COMPRESSION] = Compression.GZIP.value
        os.environ[OTEL_EXPORTER_OTLP_ENDPOINT] = OS_ENV_ENDPOINT
        os.environ[OTEL_EXPORTER_OTLP_HEADERS] = OS_ENV_HEADERS
        os.environ[OTEL_EXPORTER_OTLP_INSECURE] = "true"
        os.environ[OTEL_EXPORTER_OTLP_TIMEOUT] = OS_ENV_TIMEOUT

        exporter = OTLPSpanExporter(Protocol.HTTP_PROTOBUF)

        self.assertIsInstance(exporter._encoder, ProtobufEncoder)
        self.assertIsInstance(exporter._sender, HttpSender)

        mock_http_sender.assert_called_once_with(
            OS_ENV_ENDPOINT,
            True,
            None,
            {"envHeader1": "val1", "envHeader2": "val2"},
            int(OS_ENV_TIMEOUT),
            Compression.GZIP,
        )

    @patch("opentelemetry.exporter.otlp.sender.grpc.GrpcSender.__init__")
    def test_constructor_malformed_header_arg(self, mock_grpc_sender):
        mock_grpc_sender.return_value = None

        os.environ[
            OTEL_EXPORTER_OTLP_HEADERS
        ] = "envHeader1=val1,envHeader2=val2,missingValue"

        with self.assertLogs(level="WARNING") as cm:
            exporter = OTLPSpanExporter(protocol=Protocol.GRPC)

            self.assertEqual(
                cm.records[0].message,
                "Skipped invalid OTLP exporter header: 'missingValue'",
            )

        self.assertIsInstance(exporter._encoder, ProtobufEncoder)
        self.assertIsInstance(exporter._sender, GrpcSender)

        mock_grpc_sender.assert_called_once_with(
            DEFAULT_ENDPOINT,
            DEFAULT_INSECURE,
            None,
            {"envHeader1": "val1", "envHeader2": "val2"},
            DEFAULT_TIMEOUT,
            DEFAULT_COMPRESSION,
        )
