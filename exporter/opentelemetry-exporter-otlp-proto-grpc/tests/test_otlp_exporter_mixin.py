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

import time
from concurrent.futures import ThreadPoolExecutor
from logging import WARNING
from unittest import TestCase
from unittest.mock import Mock, patch

from google.protobuf.duration_pb2 import (  # pylint: disable=no-name-in-module
    Duration,
)
from google.rpc.error_details_pb2 import (  # pylint: disable=no-name-in-module
    RetryInfo,
)
from grpc import Compression, server

from opentelemetry.exporter.otlp.proto.common._internal import (
    ThreadWithReturnValue,
)
from opentelemetry.exporter.otlp.proto.grpc.exporter import (
    InvalidCompressionValueException,
    StatusCode,
    environ_to_compression,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceResponse,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import (
    TraceServiceServicer,
    add_TraceServiceServicer_to_server,
)
from opentelemetry.sdk.trace import _Span
from opentelemetry.sdk.trace.export import (
    SpanExportResult,
)


class TraceServiceServicerWithExportParams(TraceServiceServicer):
    def __init__(
        self,
        export_result,
        optional_export_sleep=None,
        optional_export_retry=None,
    ):
        self.export_result = export_result
        self.optional_export_sleep = optional_export_sleep
        self.optional_export_retry = optional_export_retry

    # pylint: disable=invalid-name,unused-argument,no-self-use
    def Export(self, request, context):
        if self.optional_export_sleep:
            time.sleep(self.optional_export_sleep)
        if self.optional_export_retry:
            context.send_initial_metadata(
                (
                    (
                        "google.rpc.retryinfo-bin",
                        RetryInfo().SerializeToString(),
                    ),
                )
            )
            context.set_trailing_metadata(
                (
                    (
                        "google.rpc.retryinfo-bin",
                        RetryInfo(
                            retry_delay=Duration(
                                seconds=self.optional_export_retry
                            )
                        ).SerializeToString(),
                    ),
                )
            )
        context.set_code(self.export_result)

        return ExportTraceServiceResponse()


class TestOTLPExporterMixin(TestCase):
    def setUp(self):
        self.server = server(ThreadPoolExecutor(max_workers=10))

        self.server.add_insecure_port("127.0.0.1:4317")

        self.server.start()
        self.exporter = OTLPSpanExporter(insecure=True)
        self.span = _Span(
            "a",
            context=Mock(
                **{
                    "trace_state": {"a": "b", "c": "d"},
                    "span_id": 10217189687419569865,
                    "trace_id": 67545097771067222548457157018666467027,
                }
            ),
        )

    def tearDown(self):
        self.server.stop(None)

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

    def test_ignore_export_after_shutdown(self):
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(StatusCode.OK),
            self.server,
        )
        self.exporter.shutdown()
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                self.exporter.export([self.span]), SpanExportResult.FAILURE
            )
            self.assertEqual(
                warning.records[0].message,
                "Exporter already shutdown, ignoring batch",
            )

    def test_shutdown_wait_last_export(self):
        # Shutdown waits 30 seconds for a pending Export call to finish.
        # A 5 second delay is added, so it's expected that export will finish.
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(StatusCode.OK, 5),
            self.server,
        )

        export_thread = ThreadWithReturnValue(
            target=self.exporter.export, args=([self.span],)
        )
        export_thread.start()
        # Wait a sec for the export call.
        time.sleep(1)
        # pylint: disable=protected-access
        self.assertFalse(self.exporter._export_not_occuring.is_set())
        # Should block until export is finished
        self.exporter.shutdown()
        # pylint: disable=protected-access
        self.assertTrue(self.exporter._export_not_occuring.is_set())
        # pylint: disable=protected-access
        self.assertTrue(self.exporter._shutdown_occuring.is_set())
        export_result = export_thread.join()
        self.assertEqual(export_result, SpanExportResult.SUCCESS)

    def test_shutdown_doesnot_wait_last_export(self):
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(StatusCode.OK, 35),
            self.server,
        )

        export_thread = ThreadWithReturnValue(
            target=self.exporter.export, args=([self.span],)
        )
        export_thread.start()
        # Wait a sec for exporter to get lock and make export call.
        time.sleep(1)
        # pylint: disable=protected-access
        self.assertFalse(self.exporter._export_not_occuring.is_set())
        # Set to 6 seconds, so the 35 second server-side delay will not be reached.
        self.exporter.shutdown(timeout_millis=6000)
        # pylint: disable=protected-access
        self.assertFalse(self.exporter._export_not_occuring.is_set())
        # pylint: disable=protected-access
        self.assertTrue(self.exporter._shutdown_occuring.is_set())
        export_result = export_thread.join()
        self.assertEqual(export_result, SpanExportResult.FAILURE)

    def test_shutdown_interrupts_export_sleep(self):
        # Returns unavailable and asks for a 20 second sleep before retry.
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(
                StatusCode.UNAVAILABLE, 0, 20
            ),
            self.server,
        )

        export_thread = ThreadWithReturnValue(
            target=self.exporter.export, args=([self.span],)
        )
        export_thread.start()
        # Wait a sec for call to fail and export sleep to begin.
        time.sleep(1)
        begin_wait = time.time_ns()
        # pylint: disable=protected-access
        self.assertTrue(self.exporter._export_not_occuring.is_set())
        self.exporter.shutdown()
        self.assertTrue(self.exporter._shutdown_occuring.is_set())
        # pylint: disable=protected-access
        export_result = export_thread.join()
        end_wait = time.time_ns()
        self.assertEqual(export_result, SpanExportResult.FAILURE)
        # Less than a second for export to finish, because the 20 second sleep is interurpted by shutdown event.
        self.assertTrue((end_wait - begin_wait) <  1e9)

    def test_export_over_closed_grpc_channel(self):
        # pylint: disable=protected-access

        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(StatusCode.OK),
            self.server,
        )
        self.exporter.shutdown()
        data = self.exporter._translate_data([self.span])
        with self.assertRaises(ValueError) as err:
            self.exporter._client.Export(request=data)
        self.assertEqual(
            str(err.exception), "Cannot invoke RPC on closed channel!"
        )
