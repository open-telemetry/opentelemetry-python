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

import threading
from logging import WARNING
from time import time_ns
from types import MethodType
from typing import Sequence
from unittest import TestCase
from unittest.mock import Mock, patch

from google.protobuf.duration_pb2 import (  # pylint: disable=no-name-in-module
    Duration,
)
from google.rpc.error_details_pb2 import RetryInfo
from grpc import Compression

from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    ExportServiceRequestT,
    InvalidCompressionValueException,
    OTLPExporterMixin,
    RpcError,
    SDKDataT,
    StatusCode,
    environ_to_compression,
)


class TestOTLPExporterMixin(TestCase):
    def test_environ_to_compression(self):
        with patch.dict(
            "os.environ",
            {
                "test_gzip": "gzip",
                "test_gzip_caseinsensitive_with_whitespace": " GzIp ",
                "test_invalid": "some invalid compression",
            },
        ):
            self.assertEqual(
                environ_to_compression("test_gzip"), Compression.Gzip
            )
            self.assertEqual(
                environ_to_compression(
                    "test_gzip_caseinsensitive_with_whitespace"
                ),
                Compression.Gzip,
            )
            self.assertIsNone(
                environ_to_compression("missing_key"),
            )
            with self.assertRaises(InvalidCompressionValueException):
                environ_to_compression("test_invalid")

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter._create_exp_backoff_generator"
    )
    def test_export_warning(self, mock_expo):
        mock_expo.configure_mock(**{"return_value": [0]})

        rpc_error = RpcError()

        def code(self):
            return None

        rpc_error.code = MethodType(code, rpc_error)

        class OTLPMockExporter(OTLPExporterMixin):
            _result = Mock()
            _stub = Mock(
                **{"return_value": Mock(**{"Export.side_effect": rpc_error})}
            )

            def _translate_data(
                self, data: Sequence[SDKDataT]
            ) -> ExportServiceRequestT:
                pass

            @property
            def _exporting(self) -> str:
                return "mock"

        otlp_mock_exporter = OTLPMockExporter()

        with self.assertLogs(level=WARNING) as warning:
            # pylint: disable=protected-access
            otlp_mock_exporter._export(Mock())
            self.assertEqual(
                warning.records[0].message,
                "Failed to export mock to localhost:4317, error code: None",
            )

        def code(self):  # pylint: disable=function-redefined
            return StatusCode.CANCELLED

        def trailing_metadata(self):
            return {}

        rpc_error.code = MethodType(code, rpc_error)
        rpc_error.trailing_metadata = MethodType(trailing_metadata, rpc_error)

        with self.assertLogs(level=WARNING) as warning:
            # pylint: disable=protected-access
            otlp_mock_exporter._export([])
            self.assertEqual(
                warning.records[0].message,
                (
                    "Transient error StatusCode.CANCELLED encountered "
                    "while exporting mock to localhost:4317, retrying in 0s."
                ),
            )

    def test_shutdown(self):
        result_mock = Mock()

        class OTLPMockExporter(OTLPExporterMixin):
            _result = result_mock
            _stub = Mock(**{"return_value": Mock()})

            def _translate_data(
                self, data: Sequence[SDKDataT]
            ) -> ExportServiceRequestT:
                pass

            @property
            def _exporting(self) -> str:
                return "mock"

        otlp_mock_exporter = OTLPMockExporter()

        with self.assertLogs(level=WARNING) as warning:
            # pylint: disable=protected-access
            self.assertEqual(
                otlp_mock_exporter._export(data={}), result_mock.SUCCESS
            )
            otlp_mock_exporter.shutdown()
            # pylint: disable=protected-access
            self.assertEqual(
                otlp_mock_exporter._export(data={}), result_mock.FAILURE
            )
            self.assertEqual(
                warning.records[0].message,
                "Exporter already shutdown, ignoring batch",
            )

    def test_shutdown_wait_last_export(self):
        result_mock = Mock()
        rpc_error = RpcError()

        def code(self):
            return StatusCode.UNAVAILABLE

        def trailing_metadata(self):
            return {
                "google.rpc.retryinfo-bin": RetryInfo(
                    retry_delay=Duration(nanos=int(1e7))
                ).SerializeToString()
            }

        rpc_error.code = MethodType(code, rpc_error)
        rpc_error.trailing_metadata = MethodType(trailing_metadata, rpc_error)

        class OTLPMockExporter(OTLPExporterMixin):
            _result = result_mock
            _stub = Mock(
                **{"return_value": Mock(**{"Export.side_effect": rpc_error})}
            )

            def _translate_data(
                self, data: Sequence[SDKDataT]
            ) -> ExportServiceRequestT:
                pass

            @property
            def _exporting(self) -> str:
                return "mock"

        otlp_mock_exporter = OTLPMockExporter()

        # pylint: disable=protected-access
        export_thread = threading.Thread(
            target=otlp_mock_exporter._export, args=({},)
        )
        export_thread.start()
        try:
            # pylint: disable=protected-access
            self.assertTrue(otlp_mock_exporter._export_lock.locked())
            # delay is 1 second while the default shutdown timeout is 30_000 milliseconds
            start_time = time_ns()
            otlp_mock_exporter.shutdown()
            now = time_ns()
            self.assertGreaterEqual(now, (start_time + 30 / 1000))
            # pylint: disable=protected-access
            self.assertTrue(otlp_mock_exporter._shutdown)
            # pylint: disable=protected-access
            self.assertFalse(otlp_mock_exporter._export_lock.locked())
        finally:
            export_thread.join()
