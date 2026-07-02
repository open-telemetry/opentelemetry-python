# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import gzip
import time
import zlib
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from queue import Empty, Queue
from threading import Thread
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from opentelemetry.proto.common.v1.common_pb2 import InstrumentationScope
    from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord
    from opentelemetry.proto.metrics.v1.metrics_pb2 import Metric
    from opentelemetry.proto.resource.v1.resource_pb2 import Resource
    from opentelemetry.proto.trace.v1.trace_pb2 import Span


@dataclass
class RecordedSpan:
    span: Span
    resource: Resource
    scope: InstrumentationScope


@dataclass
class RecordedMetric:
    metric: Metric
    resource: Resource
    scope: InstrumentationScope


@dataclass
class RecordedLogRecord:
    log_record: LogRecord
    resource: Resource
    scope: InstrumentationScope


def _make_handler(
    spans_queue: Queue[RecordedSpan],
    metrics_queue: Queue[RecordedMetric],
    logs_queue: Queue[RecordedLogRecord],
    traces_path: str,
    metrics_path: str,
    logs_path: str,
) -> type[BaseHTTPRequestHandler]:
    # pylint: disable=import-outside-toplevel,no-name-in-module
    from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (  # noqa: PLC0415
        ExportLogsServiceRequest,
        ExportLogsServiceResponse,
    )
    from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (  # noqa: PLC0415
        ExportMetricsServiceRequest,
        ExportMetricsServiceResponse,
    )
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (  # noqa: PLC0415
        ExportTraceServiceRequest,
        ExportTraceServiceResponse,
    )

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # pylint: disable=invalid-name
            content_length = int(self.headers.get("Content-Length", 0))
            body = self._decompress(self.rfile.read(content_length))
            path = urlparse(self.path).path

            if path == traces_path:
                response_body = self._handle_traces(body)
            elif path == metrics_path:
                response_body = self._handle_metrics(body)
            elif path == logs_path:
                response_body = self._handle_logs(body)
            else:
                self.send_error(404)
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/x-protobuf")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)

        def _decompress(self, body: bytes) -> bytes:
            encoding = self.headers.get("Content-Encoding", "")
            if encoding == "gzip":
                return gzip.decompress(body)
            if encoding == "deflate":
                return zlib.decompress(body)
            return body

        @staticmethod
        def _handle_traces(body: bytes) -> bytes:
            request = ExportTraceServiceRequest()
            request.ParseFromString(body)
            for rs in request.resource_spans:
                for ss in rs.scope_spans:
                    for span in ss.spans:
                        spans_queue.put(
                            RecordedSpan(
                                span=span, resource=rs.resource, scope=ss.scope
                            )
                        )
            return ExportTraceServiceResponse().SerializeToString()

        @staticmethod
        def _handle_metrics(body: bytes) -> bytes:
            request = ExportMetricsServiceRequest()
            request.ParseFromString(body)
            for rm in request.resource_metrics:
                for sm in rm.scope_metrics:
                    for metric in sm.metrics:
                        metrics_queue.put(
                            RecordedMetric(
                                metric=metric,
                                resource=rm.resource,
                                scope=sm.scope,
                            )
                        )
            return ExportMetricsServiceResponse().SerializeToString()

        @staticmethod
        def _handle_logs(body: bytes) -> bytes:
            request = ExportLogsServiceRequest()
            request.ParseFromString(body)
            for rl in request.resource_logs:
                for sl in rl.scope_logs:
                    for log_record in sl.log_records:
                        logs_queue.put(
                            RecordedLogRecord(
                                log_record=log_record,
                                resource=rl.resource,
                                scope=sl.scope,
                            )
                        )
            return ExportLogsServiceResponse().SerializeToString()

        def log_message(self, format, *args):  # pylint: disable=redefined-builtin
            pass

    return _Handler


class OtlpProtoTestServer:
    def __init__(
        self, host: str = "127.0.0.1", port: int = 0, base_path: str = ""
    ) -> None:
        try:
            # pylint: disable-next=import-outside-toplevel,unused-import
            import opentelemetry.proto  # noqa: F401, PLC0415
        except ImportError:
            raise ImportError(
                "opentelemetry-proto is required to use OtlpProtoTestServer. "
                "Install it with: pip install opentelemetry-proto"
            ) from None
        self._host = host
        self._port = port
        self._base_path = base_path.rstrip("/")
        self._spans_queue: Queue[RecordedSpan] = Queue()
        self._metrics_queue: Queue[RecordedMetric] = Queue()
        self._logs_queue: Queue[RecordedLogRecord] = Queue()
        self._server: HTTPServer | None = None
        self._thread: Thread | None = None

    def start(self) -> OtlpProtoTestServer:
        handler = _make_handler(
            self._spans_queue,
            self._metrics_queue,
            self._logs_queue,
            f"{self._base_path}/v1/traces",
            f"{self._base_path}/v1/metrics",
            f"{self._base_path}/v1/logs",
        )
        self._server = HTTPServer((self._host, self._port), handler)
        self._port = self._server.server_address[1]
        self._thread = Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="OtlpProtoTestServer",
        )
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            if self._thread is not None:
                self._thread.join()
            self._server.server_close()

    def __enter__(self) -> OtlpProtoTestServer:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    @property
    def port(self) -> int:
        return self._port

    @property
    def traces_endpoint(self) -> str:
        return f"http://{self._host}:{self._port}{self._base_path}/v1/traces"

    @property
    def metrics_endpoint(self) -> str:
        return f"http://{self._host}:{self._port}{self._base_path}/v1/metrics"

    @property
    def logs_endpoint(self) -> str:
        return f"http://{self._host}:{self._port}{self._base_path}/v1/logs"

    def get_span(self, timeout: float = 5.0) -> RecordedSpan:
        try:
            return self._spans_queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError(f"No span received within {timeout}s") from None

    def get_spans(
        self, count: int = 1, timeout: float = 5.0
    ) -> list[RecordedSpan]:
        deadline = time.monotonic() + timeout
        spans = []
        for _ in range(count):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Timed out after receiving {len(spans)}/{count} spans"
                )
            spans.append(self.get_span(timeout=remaining))
        return spans

    def wait_for_span(
        self, *, name: str | None = None, timeout: float = 5.0
    ) -> RecordedSpan:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"No span with name={name!r} received within {timeout}s"
                )
            try:
                recorded = self._spans_queue.get(timeout=remaining)
            except Empty:
                raise TimeoutError(
                    f"No span with name={name!r} received within {timeout}s"
                ) from None
            if name is None or recorded.span.name == name:
                return recorded

    def drain_spans(self) -> list[RecordedSpan]:
        result = []
        while True:
            try:
                result.append(self._spans_queue.get_nowait())
            except Empty:
                return result

    def get_metric(self, timeout: float = 5.0) -> RecordedMetric:
        try:
            return self._metrics_queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError(
                f"No metric received within {timeout}s"
            ) from None

    def get_metrics(
        self, count: int = 1, timeout: float = 5.0
    ) -> list[RecordedMetric]:
        deadline = time.monotonic() + timeout
        metrics = []
        for _ in range(count):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Timed out after receiving {len(metrics)}/{count} metrics"
                )
            metrics.append(self.get_metric(timeout=remaining))
        return metrics

    def wait_for_metric(
        self, *, name: str | None = None, timeout: float = 5.0
    ) -> RecordedMetric:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"No metric with name={name!r} received within {timeout}s"
                )
            try:
                recorded = self._metrics_queue.get(timeout=remaining)
            except Empty:
                raise TimeoutError(
                    f"No metric with name={name!r} received within {timeout}s"
                ) from None
            if name is None or recorded.metric.name == name:
                return recorded

    def drain_metrics(self) -> list[RecordedMetric]:
        result = []
        while True:
            try:
                result.append(self._metrics_queue.get_nowait())
            except Empty:
                return result

    def get_log_record(self, timeout: float = 5.0) -> RecordedLogRecord:
        try:
            return self._logs_queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError(
                f"No log record received within {timeout}s"
            ) from None

    def get_log_records(
        self, count: int = 1, timeout: float = 5.0
    ) -> list[RecordedLogRecord]:
        deadline = time.monotonic() + timeout
        log_records = []
        for _ in range(count):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Timed out after receiving {len(log_records)}/{count} log records"
                )
            log_records.append(self.get_log_record(timeout=remaining))
        return log_records

    def wait_for_log_record(
        self, *, timeout: float = 5.0
    ) -> RecordedLogRecord:
        try:
            return self._logs_queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError(
                f"No log record received within {timeout}s"
            ) from None

    def drain_log_records(self) -> list[RecordedLogRecord]:
        result = []
        while True:
            try:
                result.append(self._logs_queue.get_nowait())
            except Empty:
                return result

    def clear(self) -> None:
        for queue in (
            self._spans_queue,
            self._metrics_queue,
            self._logs_queue,
        ):
            while True:
                try:
                    queue.get_nowait()
                except Empty:
                    break
