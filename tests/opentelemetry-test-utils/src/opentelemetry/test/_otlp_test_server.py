# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""An in-process OTLP/HTTP receiver for tests of the OTLP exporters.

:class:`OtlpProtoTestServer` listens on a loopback port, accepts the protobuf
over HTTP that the OTLP exporters send, and puts every span, metric and log
record it decodes on a queue a test can read. A request on one of the three
OTLP paths whose body the protobuf parser accepts is answered with the empty
success response of the corresponding service, so the exporter under test sees
an ordinary successful export. ``do_POST`` describes the two cases answered
otherwise.

The module is private, because the queue-per-signal shape and the ``Recorded*``
dataclasses are chosen to suit the exporter tests in this repository.

``opentelemetry-proto`` is imported lazily, so importing this module costs
nothing when the server is not used. Constructing the server without that
distribution installed raises ``ImportError`` with an explanation.
"""

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
    """One span received by the server, with the context it arrived in.

    An OTLP request nests spans under a scope and a resource, so a span taken
    out of it on its own has lost both. This keeps the three together.

    Attributes:
        span: The protobuf span, as received. It is the object from the parsed
            request, not a copy.
        resource: The protobuf resource of the ``ResourceSpans`` the span
            arrived in.
        scope: The protobuf instrumentation scope of the ``ScopeSpans`` the
            span arrived in.
        resource_schema_url: Schema URL declared on the ``ResourceSpans``, which
            is the empty string when the exporter sent none.
    """

    span: Span
    resource: Resource
    scope: InstrumentationScope
    resource_schema_url: str = ""


@dataclass
class RecordedMetric:
    """One metric received by the server, with the context it arrived in.

    Attributes:
        metric: The protobuf metric, as received, carrying all of its data
            points.
        resource: The protobuf resource of the ``ResourceMetrics`` the metric
            arrived in.
        scope: The protobuf instrumentation scope of the ``ScopeMetrics`` the
            metric arrived in.
        resource_schema_url: Schema URL declared on the ``ResourceMetrics``,
            which is the empty string when the exporter sent none.
    """

    metric: Metric
    resource: Resource
    scope: InstrumentationScope
    resource_schema_url: str = ""


@dataclass
class RecordedLogRecord:
    """One log record received by the server, with the context it arrived in.

    Attributes:
        log_record: The protobuf log record, as received.
        resource: The protobuf resource of the ``ResourceLogs`` the record
            arrived in.
        scope: The protobuf instrumentation scope of the ``ScopeLogs`` the
            record arrived in.
        resource_schema_url: Schema URL declared on the ``ResourceLogs``, which
            is the empty string when the exporter sent none.
    """

    log_record: LogRecord
    resource: Resource
    scope: InstrumentationScope
    resource_schema_url: str = ""


def _make_handler(
    spans_queue: Queue[RecordedSpan],
    metrics_queue: Queue[RecordedMetric],
    logs_queue: Queue[RecordedLogRecord],
    traces_path: str,
    metrics_path: str,
    logs_path: str,
) -> type[BaseHTTPRequestHandler]:
    """Build a request handler class bound to given queues and paths.

    The handler is built here rather than defined at module level for two
    reasons: the generated protobuf modules are imported inside this function,
    so importing this module does not require ``opentelemetry-proto``, and the
    queues and paths are closed over, so the handler needs no per-instance
    configuration that ``HTTPServer`` has no way to supply.

    Args:
        spans_queue: Queue that each decoded span is put on, one
            :class:`RecordedSpan` per span.
        metrics_queue: Queue that each decoded metric is put on.
        logs_queue: Queue that each decoded log record is put on.
        traces_path: Request path that carries ``ExportTraceServiceRequest``
            bodies, compared for equality after the query string is stripped.
        metrics_path: Request path that carries
            ``ExportMetricsServiceRequest`` bodies.
        logs_path: Request path that carries ``ExportLogsServiceRequest``
            bodies.

    Returns:
        A ``BaseHTTPRequestHandler`` subclass. Each call returns a new class
        closing over the arguments of that call.

    Raises:
        ImportError: When ``opentelemetry-proto`` is not installed.
    """
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
        """Handler that decodes an OTLP export request onto the right queue."""

        def do_POST(self):  # pylint: disable=invalid-name
            """Decode one export request and answer with the success response.

            The path decides which signal the body holds. A path matching none
            of the three is answered with ``404`` and nothing is queued. A
            recognised path whose body the protobuf parser accepts is answered
            with ``200`` and the empty success response of that OTLP service,
            so partial success is never reported. A body the parser rejects
            raises out of this method instead, and the connection is closed
            with no status line, so the exporter sees a transport failure and
            takes the retry path.
            """
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
            """Undo the compression named by the ``Content-Encoding`` header.

            Args:
                body: The raw request body.

            Returns:
                The decompressed body for ``gzip`` and ``deflate``, and the
                body unchanged for any other encoding including an absent
                header. An encoding the exporter applied that is not one of
                those two therefore reaches the protobuf parser compressed and
                fails there.
            """
            encoding = self.headers.get("Content-Encoding", "")
            if encoding == "gzip":
                return gzip.decompress(body)
            if encoding == "deflate":
                return zlib.decompress(body)
            return body

        @staticmethod
        def _handle_traces(body: bytes) -> bytes:
            """Queue every span in a trace export request.

            Args:
                body: The decompressed ``ExportTraceServiceRequest`` protobuf.

            Returns:
                A serialized empty ``ExportTraceServiceResponse``, which tells
                the exporter that every span was accepted.
            """
            request = ExportTraceServiceRequest()
            request.ParseFromString(body)
            for rs in request.resource_spans:
                for ss in rs.scope_spans:
                    for span in ss.spans:
                        spans_queue.put(
                            RecordedSpan(
                                span=span,
                                resource=rs.resource,
                                scope=ss.scope,
                                resource_schema_url=rs.schema_url,
                            )
                        )
            return ExportTraceServiceResponse().SerializeToString()

        @staticmethod
        def _handle_metrics(body: bytes) -> bytes:
            """Queue every metric in a metrics export request.

            Args:
                body: The decompressed ``ExportMetricsServiceRequest``
                    protobuf.

            Returns:
                A serialized empty ``ExportMetricsServiceResponse``.
            """
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
                                resource_schema_url=rm.schema_url,
                            )
                        )
            return ExportMetricsServiceResponse().SerializeToString()

        @staticmethod
        def _handle_logs(body: bytes) -> bytes:
            """Queue every log record in a logs export request.

            Args:
                body: The decompressed ``ExportLogsServiceRequest`` protobuf.

            Returns:
                A serialized empty ``ExportLogsServiceResponse``.
            """
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
                                resource_schema_url=rl.schema_url,
                            )
                        )
            return ExportLogsServiceResponse().SerializeToString()

        def log_message(self, format, *args):  # pylint: disable=redefined-builtin
            """Discard the access log line ``BaseHTTPRequestHandler`` writes.

            The default implementation writes to stderr, which would put a line
            per export into the output of every passing test.

            Args:
                format: Printf-style format string of the line to discard.
                *args: Values the format string would have been given.
            """

    return _Handler


class OtlpProtoTestServer:
    """An OTLP/HTTP receiver that keeps what it receives in memory.

    Use it as a context manager, which starts it on entry and stops it on exit::

        with OtlpProtoTestServer() as server:
            exporter = OTLPSpanExporter(endpoint=server.traces_endpoint)
            exporter.export([span])
            recorded = server.wait_for_span(name="my-span")

    The three endpoint properties give the URLs to configure an exporter with.
    Under the default ``port`` of ``0`` they are meaningful only after
    ``start``, because the port is assigned on bind; when an explicit port was
    requested they already hold it before ``start``.
    Received telemetry is read either by waiting for a specific item, with
    ``get_span``, ``wait_for_span`` and their metric and log counterparts, or by
    taking whatever has arrived, with ``drain_spans``, ``drain_metrics`` and
    ``drain_log_records``. Every read removes what it returns, so an item is
    seen once. A waiting read also removes and discards what it passes over: a
    ``wait_for_*`` call drops every non-matching item it takes off the queue,
    and a ``get_*`` call that gives up drops the items it had already collected
    along with raising ``TimeoutError``.

    Requests are served from a single daemon thread, so exports are decoded one
    at a time in the order they arrive.

    Args:
        host: Address to bind to. The default keeps the server off the network.
        port: Port to bind to. The default of ``0`` lets the operating system
            choose a free one, which is what lets several tests run at once;
            read the chosen port from the ``port`` property after ``start``.
        base_path: Prefix the three OTLP paths are served under, for example
            ``/otlp`` to serve ``/otlp/v1/traces``. A trailing slash is
            stripped. The default serves ``/v1/traces``, ``/v1/metrics`` and
            ``/v1/logs``, which is where an exporter looks by default.

    Raises:
        ImportError: When ``opentelemetry-proto`` is not installed, since the
            server cannot decode a request without it.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0, base_path: str = "") -> None:
        """Parameters are documented on the class docstring."""
        try:
            # pylint: disable-next=import-outside-toplevel,unused-import
            import opentelemetry.proto  # noqa: PLC0415, F401
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
        """Bind the socket and serve requests from a background thread.

        Returns:
            This server, so the call can be chained. After it returns, ``port``
            holds the bound port and the three endpoint properties are usable.

        Raises:
            OSError: When the address and port cannot be bound, which is what
                happens when an explicit ``port`` is already in use.
        """
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
        """Stop serving, join the thread and close the socket.

        Does nothing when the server was never started. Queued telemetry is
        kept, so a test may read it after stopping. Calling ``start`` again
        builds a new ``HTTPServer`` and works, and it rebinds the port assigned
        to the previous run rather than asking for a new one, because that port
        was written over the ``0`` requested at construction.
        """
        if self._server is not None:
            self._server.shutdown()
            if self._thread is not None:
                self._thread.join()
            self._server.server_close()

    def __enter__(self) -> OtlpProtoTestServer:
        """Start the server for the duration of the block.

        Returns:
            This server, already serving.
        """
        return self.start()

    def __exit__(self, *exc: object) -> None:
        """Stop the server, whether the block completed or raised.

        Args:
            *exc: The exception type, value and traceback that ``with``
                supplies. They are ignored, so an exception raised in the block
                propagates.
        """
        self.stop()

    @property
    def port(self) -> int:
        """Return the TCP port the server listens on.

        Returns:
            The port assigned by the operating system once ``start`` has bound
            the socket, or the port requested at construction before that. It
            is ``0`` before ``start`` when no explicit port was requested.
        """
        return self._port

    @property
    def traces_endpoint(self) -> str:
        """Return the URL to configure a span exporter with.

        Returns:
            The full ``http://`` URL of the traces path, including the base
            path. Under the default ``port`` of ``0`` it is meaningful only
            after ``start``, since the port is part of it; an explicit port is
            already in the URL before that. The scheme is plain HTTP, so an
            exporter has to be configured not to use TLS.
        """
        return f"http://{self._host}:{self._port}{self._base_path}/v1/traces"

    @property
    def metrics_endpoint(self) -> str:
        """Return the URL to configure a metric exporter with.

        Returns:
            The full ``http://`` URL of the metrics path, including the base
            path, meaningful under the same condition as ``traces_endpoint``.
        """
        return f"http://{self._host}:{self._port}{self._base_path}/v1/metrics"

    @property
    def logs_endpoint(self) -> str:
        """Return the URL to configure a log exporter with.

        Returns:
            The full ``http://`` URL of the logs path, including the base path,
            meaningful under the same condition as ``traces_endpoint``.
        """
        return f"http://{self._host}:{self._port}{self._base_path}/v1/logs"

    def get_span(self, timeout: float = 5.0) -> RecordedSpan:
        """Take the next span off the queue, waiting for one to arrive.

        Args:
            timeout: Seconds to wait before giving up.

        Returns:
            The oldest span not yet taken, removed from the queue.

        Raises:
            TimeoutError: When no span arrives within ``timeout``.
        """
        try:
            return self._spans_queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError(f"No span received within {timeout}s") from None

    def get_spans(self, count: int = 1, timeout: float = 5.0) -> list[RecordedSpan]:
        """Take a given number of spans off the queue.

        Args:
            count: How many spans to collect.
            timeout: Seconds to wait for all of them together, not for each
                one, so the call returns within roughly this long however the
                spans are spread out.

        Returns:
            A list of ``count`` spans, oldest first, removed from the queue.

        Raises:
            TimeoutError: When fewer than ``count`` spans arrive in time. The
                spans already taken off the queue are discarded with the
                exception. The message names how many were collected only when
                the deadline passes between two successful reads; the usual
                case is the timeout of the read itself, which names no count.
        """
        deadline = time.monotonic() + timeout
        spans = []
        for _ in range(count):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Timed out after receiving {len(spans)}/{count} spans")
            spans.append(self.get_span(timeout=remaining))
        return spans

    def wait_for_span(self, *, name: str | None = None, timeout: float = 5.0) -> RecordedSpan:
        """Wait for a span with a given name, discarding the ones before it.

        Args:
            name: Exact span name to wait for. ``None`` accepts the next span
                whatever its name, which makes the call equivalent to
                ``get_span``.
            timeout: Seconds to wait before giving up.

        Returns:
            The first span whose name matches, removed from the queue.

        Raises:
            TimeoutError: When no matching span arrives within ``timeout``.
                Every non-matching span taken off the queue while waiting is
                discarded, so a test that needs those has to read them first.
        """
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"No span with name={name!r} received within {timeout}s")
            try:
                recorded = self._spans_queue.get(timeout=remaining)
            except Empty:
                raise TimeoutError(f"No span with name={name!r} received within {timeout}s") from None
            if name is None or recorded.span.name == name:
                return recorded

    def drain_spans(self) -> list[RecordedSpan]:
        """Take every span queued so far, without waiting.

        Returns:
            A list of the queued spans, oldest first, leaving the queue empty.
            Nothing queued gives an empty list. Because it does not wait, an
            export still in flight is missed; flush the exporter under test
            first.
        """
        result = []
        while True:
            try:
                result.append(self._spans_queue.get_nowait())
            except Empty:
                return result

    def get_metric(self, timeout: float = 5.0) -> RecordedMetric:
        """Take the next metric off the queue, waiting for one to arrive.

        Args:
            timeout: Seconds to wait before giving up.

        Returns:
            The oldest metric not yet taken, removed from the queue. One
            exported metric is one item however many data points it carries.

        Raises:
            TimeoutError: When no metric arrives within ``timeout``.
        """
        try:
            return self._metrics_queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError(f"No metric received within {timeout}s") from None

    def get_metrics(self, count: int = 1, timeout: float = 5.0) -> list[RecordedMetric]:
        """Take a given number of metrics off the queue.

        Args:
            count: How many metrics to collect.
            timeout: Seconds to wait for all of them together.

        Returns:
            A list of ``count`` metrics, oldest first, removed from the queue.

        Raises:
            TimeoutError: When fewer than ``count`` metrics arrive in time. The
                metrics already taken off the queue are discarded with the
                exception. The message names how many were collected only when
                the deadline passes between two successful reads.
        """
        deadline = time.monotonic() + timeout
        metrics = []
        for _ in range(count):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Timed out after receiving {len(metrics)}/{count} metrics")
            metrics.append(self.get_metric(timeout=remaining))
        return metrics

    def wait_for_metric(self, *, name: str | None = None, timeout: float = 5.0) -> RecordedMetric:
        """Wait for a metric with a given name, discarding the ones before it.

        Args:
            name: Exact metric name to wait for. ``None`` accepts the next
                metric whatever its name.
            timeout: Seconds to wait before giving up.

        Returns:
            The first metric whose name matches, removed from the queue.

        Raises:
            TimeoutError: When no matching metric arrives within ``timeout``.
                Every non-matching metric taken off the queue while waiting is
                discarded, which matters more here than for spans because one
                export carries every instrument of a meter.
        """
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"No metric with name={name!r} received within {timeout}s")
            try:
                recorded = self._metrics_queue.get(timeout=remaining)
            except Empty:
                raise TimeoutError(f"No metric with name={name!r} received within {timeout}s") from None
            if name is None or recorded.metric.name == name:
                return recorded

    def drain_metrics(self) -> list[RecordedMetric]:
        """Take every metric queued so far, without waiting.

        Returns:
            A list of the queued metrics, oldest first, leaving the queue
            empty. Nothing queued gives an empty list.
        """
        result = []
        while True:
            try:
                result.append(self._metrics_queue.get_nowait())
            except Empty:
                return result

    def get_log_record(self, timeout: float = 5.0) -> RecordedLogRecord:
        """Take the next log record off the queue, waiting for one to arrive.

        Args:
            timeout: Seconds to wait before giving up.

        Returns:
            The oldest log record not yet taken, removed from the queue.

        Raises:
            TimeoutError: When no log record arrives within ``timeout``.
        """
        try:
            return self._logs_queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError(f"No log record received within {timeout}s") from None

    def get_log_records(self, count: int = 1, timeout: float = 5.0) -> list[RecordedLogRecord]:
        """Take a given number of log records off the queue.

        Args:
            count: How many log records to collect.
            timeout: Seconds to wait for all of them together.

        Returns:
            A list of ``count`` log records, oldest first, removed from the
            queue.

        Raises:
            TimeoutError: When fewer than ``count`` log records arrive in time.
                The records already taken off the queue are discarded with the
                exception. The message names how many were collected only when
                the deadline passes between two successful reads.
        """
        deadline = time.monotonic() + timeout
        log_records = []
        for _ in range(count):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Timed out after receiving {len(log_records)}/{count} log records")
            log_records.append(self.get_log_record(timeout=remaining))
        return log_records

    def wait_for_log_record(self, *, timeout: float = 5.0) -> RecordedLogRecord:
        """Wait for the next log record to arrive.

        There is no name to filter on, so unlike ``wait_for_span`` and
        ``wait_for_metric`` this discards nothing and is the same as
        ``get_log_record`` with a keyword-only timeout.

        Args:
            timeout: Seconds to wait before giving up.

        Returns:
            The oldest log record not yet taken, removed from the queue.

        Raises:
            TimeoutError: When no log record arrives within ``timeout``.
        """
        try:
            return self._logs_queue.get(timeout=timeout)
        except Empty:
            raise TimeoutError(f"No log record received within {timeout}s") from None

    def drain_log_records(self) -> list[RecordedLogRecord]:
        """Take every log record queued so far, without waiting.

        Returns:
            A list of the queued log records, oldest first, leaving the queue
            empty. Nothing queued gives an empty list.
        """
        result = []
        while True:
            try:
                result.append(self._logs_queue.get_nowait())
            except Empty:
                return result

    def clear(self) -> None:
        """Discard everything queued on all three signals.

        Call it between phases of a test so that telemetry from the setup phase
        is not read as telemetry from the phase under test. The server keeps
        serving, so anything exported after this call is queued normally.
        """
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
