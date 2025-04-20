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
from logging import WARNING
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
        optional_export_sleep: Optional[float] = None,
        optional_export_retry_millis: Optional[float] = None,
    ):
        self.export_result = export_result
        self.optional_export_sleep = optional_export_sleep
        self.optional_export_retry_millis = optional_export_retry_millis

    # pylint: disable=invalid-name,unused-argument
    def Export(self, request, context):
        if self.optional_export_sleep:
            time.sleep(self.optional_export_sleep)
        if self.optional_export_retry_millis:
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
                                nanos=int(self.optional_export_retry_millis)
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
            "localhost:4317", compression=Compression.NoCompression
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
            "localhost:4317", compression=Compression.Gzip
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

    def test_shutdown_wait_last_export(self):
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(
                StatusCode.OK, optional_export_sleep=1
            ),
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
            TraceServiceServicerWithExportParams(
                StatusCode.OK, optional_export_sleep=3
            ),
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

    @patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter._create_exp_backoff_generator"
    )
    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.sleep")
    def test_unavailable(self, mock_sleep, mock_expo):
        mock_expo.configure_mock(**{"return_value": [0.01]})

        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(StatusCode.UNAVAILABLE),
            self.server,
        )
        result = self.exporter.export([self.span])
        self.assertEqual(result, SpanExportResult.FAILURE)
        mock_sleep.assert_called_with(0.01)

    @patch("opentelemetry.exporter.otlp.proto.grpc.exporter.sleep")
    def test_unavailable_delay(self, mock_sleep):
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(
                StatusCode.UNAVAILABLE,
                optional_export_sleep=None,
                optional_export_retry_millis=1e7,
            ),
            self.server,
        )
        with self.assertLogs(level=WARNING) as warning:
            self.assertEqual(
                self.exporter.export([self.span]), SpanExportResult.FAILURE
            )
            mock_sleep.assert_called_with(0.01)

            self.assertEqual(
                warning.records[0].message,
                (
                    "Transient error StatusCode.UNAVAILABLE encountered "
                    "while exporting traces to localhost:4317, retrying in 0.01s."
                ),
            )

    def test_success(self):
        add_TraceServiceServicer_to_server(
            TraceServiceServicerWithExportParams(StatusCode.OK),
            self.server,
        )
        self.assertEqual(
            self.exporter.export([self.span]), SpanExportResult.SUCCESS
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
                TraceServiceServicerWithExportParams(
                    StatusCode.ALREADY_EXISTS
                ),
                self.server,
            )
            self.assertEqual(
                self.exporter.export([self.span]), SpanExportResult.FAILURE
            )
            self.assertEqual(
                warning.records[0].message,
                "Failed to export traces to localhost:4317, error code: StatusCode.ALREADY_EXISTS",
            )
