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
import unittest
from concurrent.futures import ThreadPoolExecutor
from logging import WARNING, getLogger
from platform import system
from typing import Any, Optional, Sequence
from unittest import TestCase
from unittest.mock import Mock, patch

from google.protobuf.duration_pb2 import (  # pylint: disable=no-name-in-module
    Duration,
)
from google.rpc.error_details_pb2 import (  # pylint: disable=no-name-in-module
    RetryInfo,
)
from grpc import Compression, StatusCode, server

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
        export_result: StatusCode,
        optional_retry_nanos: Optional[int] = None,
        optional_export_sleep: Optional[float] = None,
    ):
        self.export_result = export_result
        self.optional_export_sleep = optional_export_sleep
        self.optional_retry_nanos = optional_retry_nanos
        self.num_requests = 0

    # pylint: disable=invalid-name,unused-argument
    def Export(self, request, context):
        self.num_requests += 1
        if self.optional_export_sleep:
            time.sleep(self.optional_export_sleep)
        if self.export_result != StatusCode.OK and self.optional_retry_nanos:
            context.set_trailing_metadata(
                (
                    (
                        "google.rpc.retryinfo-bin",
                        RetryInfo(
                            retry_delay=Duration(
                                nanos=self.optional_retry_nanos
                            )
                        ).SerializeToString(),
                    ),
                )
            )
        context.set_code(self.export_result)

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
            options=(
                (
                    "grpc.primary_user_agent",
                    "OTel-OTLP-Exporter-Python/" + __version__,
                ),
            ),
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
            "localhost:4317",
            compression=Compression.Gzip,
            options=(
                (
                    "grpc.primary_user_agent",
                    "OTel-OTLP-Exporter-Python/" + __version__,
                ),
            ),
        )

    def test_shutdown(self):
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(StatusCode.OK),
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

    @unittest.skipIf(
        system() == "Windows",
        "For gRPC + windows there's some added delay in the RPCs which breaks the assertion over amount of time passed.",
    )
    def test_shutdown_interrupts_export_retry_backoff(self):
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(
                StatusCode.UNAVAILABLE,
            ),
            self.server,
        )

        export_thread = ThreadWithReturnValue(
            target=self.exporter.export, args=([self.span],)
        )
        with self.assertLogs(level=WARNING) as warning:
            begin_wait = time.time()
            export_thread.start()
            # Wait a bit for export to fail and the backoff sleep to start
            time.sleep(0.05)
            # The code should now be in a 1 second backoff.
            # pylint: disable=protected-access
            self.assertFalse(self.exporter._shutdown_in_progress.is_set())
            self.exporter.shutdown()
            self.assertTrue(self.exporter._shutdown_in_progress.is_set())
            export_result = export_thread.join()
            end_wait = time.time()
            self.assertEqual(export_result, SpanExportResult.FAILURE)
            # Shutdown should have interrupted the sleep.
            self.assertTrue(end_wait - begin_wait < 0.2)
            self.assertEqual(
                warning.records[1].message,
                "Shutdown in progress, aborting retry.",
            )

    def test_export_over_closed_grpc_channel(self):
        # pylint: disable=protected-access

        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(StatusCode.OK),
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

    @unittest.skipIf(
        system() == "Windows",
        "For gRPC + windows there's some added delay in the RPCs which breaks the assertion over amount of time passed.",
    )
    def test_retry_info_is_respected(self):
        mock_trace_service = TraceServiceServicerWithExportParams(
            StatusCode.UNAVAILABLE,
            optional_retry_nanos=200000000,  # .2 seconds
        )
        add_TraceServiceServicer_to_server(
            mock_trace_service,
            self.server,
        )
        exporter = OTLPSpanExporterForTesting(insecure=True, timeout=10)
        before = time.time()
        self.assertEqual(
            exporter.export([self.span]),
            SpanExportResult.FAILURE,
        )
        after = time.time()
        self.assertEqual(mock_trace_service.num_requests, 6)
        # 1 second plus wiggle room so the test passes consistently.
        self.assertAlmostEqual(after - before, 1, 1)

    @unittest.skipIf(
        system() == "Windows",
        "For gRPC + windows there's some added delay in the RPCs which breaks the assertion over amount of time passed.",
    )
    def test_retry_not_made_if_would_exceed_timeout(self):
        mock_trace_service = TraceServiceServicerWithExportParams(
            StatusCode.UNAVAILABLE
        )
        add_TraceServiceServicer_to_server(
            mock_trace_service,
            self.server,
        )
        exporter = OTLPSpanExporterForTesting(insecure=True, timeout=4)
        before = time.time()
        self.assertEqual(
            exporter.export([self.span]),
            SpanExportResult.FAILURE,
        )
        after = time.time()
        # Our retry starts with a 1 second backoff then doubles.
        # First call at time 0, second at time 1, third at time 3, fourth would exceed timeout.
        self.assertEqual(mock_trace_service.num_requests, 3)
        # There's a +/-20% jitter on each backoff.
        self.assertTrue(2.35 < after - before < 3.65)

    @unittest.skipIf(
        system() == "Windows",
        "For gRPC + windows there's some added delay in the RPCs which breaks the assertion over amount of time passed.",
    )
    def test_timeout_set_correctly(self):
        mock_trace_service = TraceServiceServicerWithExportParams(
            StatusCode.UNAVAILABLE, optional_export_sleep=0.25
        )
        add_TraceServiceServicer_to_server(
            mock_trace_service,
            self.server,
        )
        exporter = OTLPSpanExporterForTesting(insecure=True, timeout=1.4)
        # Should timeout after 1.4 seconds. First attempt takes .25 seconds
        # Then a 1 second sleep, then deadline exceeded after .15 seconds,
        # mid way through second call.
        with self.assertLogs(level=WARNING) as warning:
            before = time.time()
            # Eliminate the jitter.
            with patch("random.uniform", return_value=1):
                self.assertEqual(
                    exporter.export([self.span]),
                    SpanExportResult.FAILURE,
                )
            after = time.time()
            self.assertEqual(
                "Failed to export traces to localhost:4317, error code: StatusCode.DEADLINE_EXCEEDED",
                warning.records[-1].message,
            )
            self.assertEqual(mock_trace_service.num_requests, 2)
            self.assertAlmostEqual(after - before, 1.4, 1)

    def test_otlp_headers_from_env(self):
        # pylint: disable=protected-access
        # This ensures that there is no other header than standard user-agent.
        self.assertEqual(
            self.exporter._headers,
            (),
        )

    def test_permanent_failure(self):
        with self.assertLogs(level=WARNING) as warning:
            add_TraceServiceServicer_to_server(
                TraceServiceServicerWithExportParams(
                    StatusCode.ALREADY_EXISTS
                ),
                self.server,
            )
            self.assertEqual(
                self.exporter.export([self.span]), SpanExportResult.FAILURE
            )
            self.assertEqual(
                warning.records[-1].message,
                "Failed to export traces to localhost:4317, error code: StatusCode.ALREADY_EXISTS",
            )
