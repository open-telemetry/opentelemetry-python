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
import time
from concurrent.futures import ThreadPoolExecutor
from logging import WARNING, getLogger
from typing import Any, Optional, Sequence
from unittest import TestCase
from unittest.mock import ANY, Mock, patch

from google.rpc.code_pb2 import (  # pylint: disable=no-name-in-module
    ALREADY_EXISTS,
    OK,
    UNAVAILABLE,
)
from google.rpc.status_pb2 import Status  # pylint: disable=no-name-in-module
from grpc import Compression, server
from grpc_status import rpc_status

from opentelemetry.exporter.otlp.proto.common.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp.proto.grpc.exporter import (  # noqa: F401
    InvalidCompressionValueException,
    OTLPExporterMixin,
    environ_to_compression,
)
from opentelemetry.exporter.otlp.proto.grpc.version import __version__
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2_grpc import (
    TraceServiceServicer,
    TraceServiceStub,
    add_TraceServiceServicer_to_server,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_COMPRESSION,
)
from opentelemetry.sdk.trace import ReadableSpan, _Span
from opentelemetry.sdk.trace.export import (
    SpanExporter,
    SpanExportResult,
)

logger = getLogger(__name__)


# The below tests use this test SpanExporter and Spans, but are testing the
# underlying behavior in the mixin. A MetricExporter or LogExporter could
# just as easily be used.
class OTLPSpanExporterForTesting(
    SpanExporter,
    OTLPExporterMixin[
        ReadableSpan, ExportTraceServiceRequest, SpanExportResult
    ],
):
    _result = SpanExportResult
    _stub = TraceServiceStub

    def _translate_data(
        self, data: Sequence[ReadableSpan]
    ) -> ExportTraceServiceRequest:
        return encode_spans(data)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return self._export(spans)

    @property
    def _exporting(self):
        return "traces"

    def shutdown(self, timeout_millis=30_000):
        return OTLPExporterMixin.shutdown(self, timeout_millis)


class TraceServiceServicerWithExportParams(TraceServiceServicer):
    def __init__(
        self,
        export_result: int,
        optional_export_sleep: Optional[float] = None,
    ):
        self.export_result = export_result
        self.optional_export_sleep = optional_export_sleep

    # pylint: disable=invalid-name,unused-argument
    def Export(self, request, context):
        logger.warning("Export Request Received")
        if self.optional_export_sleep:
            time.sleep(self.optional_export_sleep)
        if self.export_result != OK:
            context.abort_with_status(
                rpc_status.to_status(
                    Status(
                        code=self.export_result,
                    )
                )
            )

        return ExportTraceServiceResponse()


class ThreadWithReturnValue(threading.Thread):
    def __init__(
        self,
        target=None,
        args=(),
    ):
        super().__init__(target=target, args=args)
        self._return = None

    def run(self):
        try:
            if self._target is not None:  # type: ignore
                self._return = self._target(*self._args, **self._kwargs)  # type: ignore
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self._target, self._args, self._kwargs  # type: ignore

    def join(self, timeout: Optional[float] = None) -> Any:
        super().join(timeout=timeout)
        return self._return


class TestOTLPExporterMixin(TestCase):
    def setUp(self):
        self.server = server(ThreadPoolExecutor(max_workers=10))

        self.server.add_insecure_port("127.0.0.1:4317")

        self.server.start()
        self.exporter = OTLPSpanExporterForTesting(insecure=True)
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

    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel")
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.secure_channel")
    def test_otlp_exporter_endpoint(self, mock_secure, mock_insecure):
        expected_endpoint = "localhost:4317"
        endpoints = [
            (
                "http://localhost:4317",
                None,
                mock_insecure,
            ),
            (
                "localhost:4317",
                None,
                mock_secure,
            ),
            (
                "http://localhost:4317",
                True,
                mock_insecure,
            ),
            (
                "localhost:4317",
                True,
                mock_insecure,
            ),
            (
                "http://localhost:4317",
                False,
                mock_secure,
            ),
            (
                "localhost:4317",
                False,
                mock_secure,
            ),
            (
                "https://localhost:4317",
                False,
                mock_secure,
            ),
            (
                "https://localhost:4317",
                None,
                mock_secure,
            ),
            (
                "https://localhost:4317",
                True,
                mock_secure,
            ),
        ]
        for endpoint, insecure, mock_method in endpoints:
            OTLPSpanExporterForTesting(endpoint=endpoint, insecure=insecure)
            self.assertEqual(
                1,
                mock_method.call_count,
                f"expected {mock_method} to be called for {endpoint} {insecure}",
            )
            self.assertEqual(
                expected_endpoint,
                mock_method.call_args[0][0],
                f"expected {expected_endpoint} got {mock_method.call_args[0][0]} {endpoint}",
            )
            mock_method.reset_mock()

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

    # pylint: disable=no-self-use
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel")
    @patch.dict("os.environ", {})
    def test_otlp_exporter_otlp_compression_unspecified(
        self, mock_insecure_channel
    ):
        """No env or kwarg should be NoCompression"""
        OTLPSpanExporterForTesting(insecure=True)
        mock_insecure_channel.assert_called_once_with(
            "localhost:4317",
            compression=Compression.NoCompression,
            options=ANY,
        )

    # pylint: disable=no-self-use, disable=unused-argument
    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.ssl_channel_credentials"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.secure_channel")
    @patch.dict("os.environ", {})
    def test_no_credentials_ssl_channel_called(
        self, secure_channel, mock_ssl_channel
    ):
        OTLPSpanExporterForTesting(insecure=False)
        self.assertTrue(mock_ssl_channel.called)

    # pylint: disable=no-self-use
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel")
    @patch.dict("os.environ", {OTEL_EXPORTER_OTLP_COMPRESSION: "gzip"})
    def test_otlp_exporter_otlp_compression_envvar(
        self, mock_insecure_channel
    ):
        """Just OTEL_EXPORTER_OTLP_COMPRESSION should work"""
        OTLPSpanExporterForTesting(insecure=True)
        mock_insecure_channel.assert_called_once_with(
            "localhost:4317", compression=Compression.Gzip, options=ANY
        )

    def test_shutdown(self):
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(OK),
            self.server,
        )
        self.assertEqual(
            self.exporter.export([self.span]), SpanExportResult.SUCCESS
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
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(OK, optional_export_sleep=1),
            self.server,
        )

        export_thread = ThreadWithReturnValue(
            target=self.exporter.export, args=([self.span],)
        )
        export_thread.start()
        # Wait a bit for exporter to get lock and make export call.
        time.sleep(0.25)
        # pylint: disable=protected-access
        self.assertTrue(self.exporter._export_lock.locked())
        self.exporter.shutdown(timeout_millis=3000)
        # pylint: disable=protected-access
        self.assertTrue(self.exporter._shutdown)
        self.assertEqual(export_thread.join(), SpanExportResult.SUCCESS)

    def test_shutdown_doesnot_wait_last_export(self):
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(OK, optional_export_sleep=3),
            self.server,
        )

        export_thread = ThreadWithReturnValue(
            target=self.exporter.export, args=([self.span],)
        )
        export_thread.start()
        # Wait for exporter to get lock and make export call.
        time.sleep(0.25)
        # pylint: disable=protected-access
        self.assertTrue(self.exporter._export_lock.locked())
        # Set to 1 seconds, so the 3 second server-side delay will not be reached.
        self.exporter.shutdown(timeout_millis=1000)
        # pylint: disable=protected-access
        self.assertTrue(self.exporter._shutdown)
        self.assertEqual(export_thread.join(), None)

    def test_export_over_closed_grpc_channel(self):
        # pylint: disable=protected-access

        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(OK),
            self.server,
        )
        self.exporter.export([self.span])
        self.exporter.shutdown()
        data = self.exporter._translate_data([self.span])
        with self.assertRaises(ValueError) as err:
            self.exporter._client.Export(request=data)
        self.assertEqual(
            str(err.exception), "Cannot invoke RPC on closed channel!"
        )

    def test_retry_timeout(self):
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(UNAVAILABLE),
            self.server,
        )
        # Set timeout to 1.5 seconds.
        exporter = OTLPSpanExporterForTesting(insecure=True, timeout=1.5)
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                exporter.export([self.span]),
                SpanExportResult.FAILURE,
            )
            # Our GRPC retry policy starts with a 1 second backoff then doubles.
            # So we expect just two calls: one at time 0, one at time 1.
            # The final log is from when export fails.
            self.assertEqual(len(warning.records), 3)
            for idx, log in enumerate(warning.records):
                if idx != 2:
                    self.assertEqual(
                        "Export Request Received",
                        log.message,
                    )
                else:
                    self.assertEqual(
                        "Failed to export traces to localhost:4317, error code: StatusCode.DEADLINE_EXCEEDED",
                        log.message,
                    )
        with self.assertLogs(level=WARNING) as warning:
            exporter = OTLPSpanExporterForTesting(insecure=True, timeout=5)
            # pylint: disable=protected-access
            self.assertEqual(exporter._timeout, 5)
            self.assertEqual(
                exporter.export([self.span]),
                SpanExportResult.FAILURE,
            )
            # We expect 3 calls: time 0, time 1, time 3, but not time 7.
            # The final log is from when export fails.
            self.assertEqual(len(warning.records), 4)
            for idx, log in enumerate(warning.records):
                if idx != 3:
                    self.assertEqual(
                        "Export Request Received",
                        log.message,
                    )
                else:
                    self.assertEqual(
                        "Failed to export traces to localhost:4317, error code: StatusCode.DEADLINE_EXCEEDED",
                        log.message,
                    )

    def test_timeout_set_correctly(self):
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(
                OK, optional_export_sleep=0.5
            ),
            self.server,
        )
        exporter = OTLPSpanExporterForTesting(insecure=True, timeout=0.4)
        # Should timeout. Deadline should be set to now + timeout.
        # That is 400 millis from now, and export sleeps for 500 millis.
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                exporter.export([self.span]),
                SpanExportResult.FAILURE,
            )
            self.assertEqual(
                "Failed to export traces to localhost:4317, error code: StatusCode.DEADLINE_EXCEEDED",
                warning.records[-1].message,
            )
        exporter = OTLPSpanExporterForTesting(insecure=True, timeout=0.8)
        self.assertEqual(
            exporter.export([self.span]),
            SpanExportResult.SUCCESS,
        )

    def test_otlp_headers_from_env(self):
        # pylint: disable=protected-access
        # This ensures that there is no other header than standard user-agent.
        self.assertEqual(
            self.exporter._headers,
            (("user-agent", "OTel-OTLP-Exporter-Python/" + __version__),),
        )

    def test_permanent_failure(self):
        with self.assertLogs(level=WARNING) as warning:
            add_TraceServiceServicer_to_server(
                TraceServiceServicerWithExportParams(ALREADY_EXISTS),
                self.server,
            )
            self.assertEqual(
                self.exporter.export([self.span]), SpanExportResult.FAILURE
            )
            self.assertEqual(
                warning.records[-1].message,
                "Failed to export traces to localhost:4317, error code: StatusCode.ALREADY_EXISTS",
            )
