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

import unittest
from unittest.mock import patch

from google.protobuf.duration_pb2 import Duration
from google.rpc.error_details_pb2 import RetryInfo
from grpc import Compression, RpcError, StatusCode

from opentelemetry.exporter.otlp.sender.grpc import GrpcSender
from opentelemetry.exporter.otlp.util import Compression as OTLPCompression
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)

CERTIFICATE_FILE = "sender/fixtures/service.crt"


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = status_code


class TestGrpcSender(unittest.TestCase):
    def test_constructor_defaults(self):
        sender = GrpcSender(
            endpoint="test.endpoint.com", certificate_file=CERTIFICATE_FILE
        )
        self.assertEqual(sender._endpoint, "test.endpoint.com")
        self.assertEqual(sender._insecure, False)
        self.assertEqual(sender._certificate_file, CERTIFICATE_FILE)
        self.assertEqual(sender._headers, None)
        self.assertEqual(sender._timeout, None)
        self.assertEqual(sender._compression, Compression.NoCompression)

    def test_constructor_explicits(self):
        sender = GrpcSender(
            endpoint="test.endpoint.com",
            insecure=True,
            certificate_file=CERTIFICATE_FILE,
            headers={"key1": "val1", "key2": "val2"},
            timeout=33,
            compression=OTLPCompression.GZIP,
        )
        self.assertEqual(sender._endpoint, "test.endpoint.com")
        self.assertEqual(sender._insecure, True)
        self.assertEqual(sender._certificate_file, CERTIFICATE_FILE)
        self.assertEqual(sender._headers, [("key1", "val1"), ("key2", "val2")])
        self.assertEqual(sender._timeout, 33)
        self.assertEqual(sender._compression, Compression.Gzip)

    def test_constructor_invalid_cert_file(self):
        with self.assertLogs(level="ERROR") as cm:
            GrpcSender(endpoint="test.endpoint.com", certificate_file="fake")
            self.assertEqual(
                cm.records[0].message,
                "Unable to read root certificates from file: 'fake'",
            )

    @patch(
        "opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc.TraceServiceStub"
    )
    def test_send_export_args(self, stub_mock):
        sender = GrpcSender(
            "test.endpoint.com",
            certificate_file=CERTIFICATE_FILE,
            headers={"key1": "val1", "key2": "val2"},
            timeout=33,
        )
        export_request = ExportTraceServiceRequest()
        sender.send(export_request)

        stub_mock.assert_called_once_with(sender._channel)
        stub_mock.return_value.Export.assert_called_once_with(
            request=export_request,
            metadata=[("key1", "val1"), ("key2", "val2")],
            timeout=33,
        )

    @patch(
        "opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc.TraceServiceStub"
    )
    def test_send_success(self, stub_mock):
        sender = GrpcSender(
            "test.endpoint.com", certificate_file=CERTIFICATE_FILE
        )
        export_request = ExportTraceServiceRequest()
        result = sender.send(export_request)

        stub_mock.assert_called_once_with(sender._channel)
        stub_mock.return_value.Export.assert_called_once_with(
            request=export_request, metadata=None, timeout=None,
        )

        self.assertTrue(result)

    @patch(
        "opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc.TraceServiceStub"
    )
    def test_send_error_code_ok(self, stub_mock):
        stub_mock.return_value.Export.side_effect = get_rpc_error(
            StatusCode.OK
        )
        sender = GrpcSender(
            "test.endpoint.com", certificate_file=CERTIFICATE_FILE
        )
        self.assertTrue(sender.send(ExportTraceServiceRequest()))

    @patch("opentelemetry.exporter.otlp.sender.grpc.sleep")
    @patch(
        "opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc.TraceServiceStub"
    )
    def test_send_unavailable_successful_retry(self, stub_mock, sleep_mock):
        stub_mock.return_value.Export.side_effect = [
            get_rpc_error(StatusCode.UNAVAILABLE),
            get_rpc_error(StatusCode.OK),
        ]

        sender = GrpcSender(
            "test.endpoint.com", certificate_file=CERTIFICATE_FILE
        )
        sender.send(ExportTraceServiceRequest())

        self.assertEqual(stub_mock.return_value.Export.call_count, 2)
        sleep_mock.assert_called_once()

    @patch("opentelemetry.exporter.otlp.sender.grpc.sleep")
    @patch(
        "opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc.TraceServiceStub"
    )
    def test_send_unavailable_max_delay(self, stub_mock, sleep_mock):
        stub_mock.return_value.Export.side_effect = get_rpc_error(
            StatusCode.UNAVAILABLE
        )

        sender = GrpcSender(
            "test.endpoint.com", certificate_file=CERTIFICATE_FILE
        )

        self.assertFalse(sender.send(ExportTraceServiceRequest()))
        self.assertEqual(stub_mock.return_value.Export.call_count, 10)
        self.assertEqual(sleep_mock.call_count, 10)


def get_rpc_error(status_code: StatusCode) -> RpcError:
    rpc_error = RpcError()
    rpc_error.code = lambda: status_code

    if status_code != StatusCode.OK:
        rpc_error.trailing_metadata = lambda: {
            "google.rpc.retryinfo-bin": RetryInfo(
                retry_delay=Duration(seconds=4)
            ).SerializeToString(),
        }

    return rpc_error
