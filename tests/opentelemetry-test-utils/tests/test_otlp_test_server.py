# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
import unittest.mock

import requests

from opentelemetry._logs import SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.test.otlp_test_server import (
    OtlpProtoTestServer,
    RecordedLogRecord,
    RecordedMetric,
    RecordedSpan,
)

try:
    # pylint: disable-next=unused-import
    import opentelemetry.proto  # noqa: F401
    from opentelemetry.exporter.otlp.proto.http import Compression
    from opentelemetry.exporter.otlp.proto.http._log_exporter import (
        OTLPLogExporter,
    )
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )

    _HAS_PROTO_DEPS = True
except ImportError:
    _HAS_PROTO_DEPS = False


@unittest.skipUnless(
    _HAS_PROTO_DEPS,
    "opentelemetry-exporter-otlp-proto-http or opentelemetry-proto are not installed",
)
class TestOtlpProtoTestServer(unittest.TestCase):
    def setUp(self):
        self.server = OtlpProtoTestServer()
        self.server.start()

    def tearDown(self):
        self.server.stop()

    def _make_trace_provider(
        self, service: str = "trace-svc", **exporter_kwargs
    ) -> TracerProvider:
        provider = TracerProvider(
            resource=Resource.create({"service.name": service})
        )
        provider.add_span_processor(
            SimpleSpanProcessor(
                OTLPSpanExporter(
                    endpoint=self.server.traces_endpoint,
                    timeout=1,
                    **exporter_kwargs,
                )
            )
        )
        return provider

    def _make_metrics_provider(
        self, service: str = "metrics-svc", **exporter_kwargs
    ) -> tuple[PeriodicExportingMetricReader, MeterProvider]:
        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=self.server.metrics_endpoint,
                timeout=1,
                **exporter_kwargs,
            ),
            export_interval_millis=100,
        )
        provider = MeterProvider(
            resource=Resource.create({"service.name": service}),
            metric_readers=[reader],
        )
        return reader, provider

    def _make_log_provider(
        self, service: str = "log-svc", **exporter_kwargs
    ) -> LoggerProvider:
        provider = LoggerProvider(
            resource=Resource.create({"service.name": service})
        )
        provider.add_log_record_processor(
            SimpleLogRecordProcessor(
                OTLPLogExporter(
                    endpoint=self.server.logs_endpoint,
                    timeout=1,
                    **exporter_kwargs,
                )
            )
        )
        return provider

    def test_span_export(self):
        provider = self._make_trace_provider()
        tracer = provider.get_tracer("trace-scope")
        with tracer.start_as_current_span("foo"):
            with tracer.start_as_current_span("bar"):
                pass
        tracer.start_span("baz").end()

        spans = self.server.get_spans(count=3, timeout=5.0)
        self.assertEqual(
            {recorded.span.name for recorded in spans}, {"foo", "bar", "baz"}
        )
        for recorded in spans:
            self.assertIsInstance(recorded, RecordedSpan)
            self.assertEqual(recorded.scope.name, "trace-scope")
            svc = next(
                a.value.string_value
                for a in recorded.resource.attributes
                if a.key == "service.name"
            )
            self.assertEqual(svc, "trace-svc")
        provider.shutdown()

    def test_wait_for_span(self):
        provider = self._make_trace_provider()
        tracer = provider.get_tracer("trace-scope")
        tracer.start_span("alpha").end()
        tracer.start_span("beta").end()

        found = self.server.wait_for_span(name="beta", timeout=5.0)
        self.assertEqual(found.span.name, "beta")
        with self.assertRaises(TimeoutError):
            self.server.get_span(timeout=0.1)
        provider.shutdown()

    def test_span_drain_and_clear(self):
        provider = self._make_trace_provider()
        tracer = provider.get_tracer("trace-scope")

        tracer.start_span("d1").end()
        tracer.start_span("d2").end()
        drained = self.server.drain_spans()
        self.assertEqual({r.span.name for r in drained}, {"d1", "d2"})

        tracer.start_span("c1").end()
        tracer.start_span("c2").end()
        self.server.clear()
        with self.assertRaises(TimeoutError):
            self.server.get_span(timeout=0.1)
        provider.shutdown()

    def test_metric_export(self):
        reader, provider = self._make_metrics_provider()
        meter = provider.get_meter("metrics-scope")
        meter.create_counter("test.requests").add(5, {"env": "test"})
        meter.create_histogram("test.latency").record(1.5, {"route": "/api"})
        reader.force_flush(timeout_millis=3000)

        metrics = self.server.get_metrics(count=2, timeout=5.0)
        self.assertEqual(
            {r.metric.name for r in metrics}, {"test.requests", "test.latency"}
        )
        for recorded in metrics:
            self.assertIsInstance(recorded, RecordedMetric)
            self.assertEqual(recorded.scope.name, "metrics-scope")
            svc = next(
                a.value.string_value
                for a in recorded.resource.attributes
                if a.key == "service.name"
            )
            self.assertEqual(svc, "metrics-svc")
        provider.shutdown()

    def test_wait_for_metric(self):
        reader, provider = self._make_metrics_provider()
        meter = provider.get_meter("metrics-scope")
        meter.create_counter("other.counter").add(1)
        meter.create_counter("target.counter").add(1)
        reader.force_flush(timeout_millis=3000)

        found = self.server.wait_for_metric(name="target.counter", timeout=5.0)
        self.assertEqual(found.metric.name, "target.counter")
        provider.shutdown()

    def test_metric_drain_and_timeout(self):
        reader, provider = self._make_metrics_provider()
        meter = provider.get_meter("metrics-scope")
        meter.create_counter("drain.counter").add(1)
        reader.force_flush(timeout_millis=3000)
        self.server.get_metric(timeout=5.0)

        self.assertEqual(self.server.drain_metrics(), [])
        provider.shutdown()
        self.server.drain_metrics()
        with self.assertRaises(TimeoutError):
            self.server.get_metric(timeout=0.1)

    def test_log_export(self):
        provider = self._make_log_provider()
        logger = provider.get_logger("log-scope")
        logger.emit(body="first message", severity_number=SeverityNumber.WARN)
        logger.emit(
            body="second message", severity_number=SeverityNumber.ERROR
        )

        log_records = self.server.get_log_records(count=2, timeout=5.0)
        self.assertEqual(
            {r.log_record.body.string_value for r in log_records},
            {"first message", "second message"},
        )
        for recorded in log_records:
            self.assertIsInstance(recorded, RecordedLogRecord)
            self.assertEqual(recorded.scope.name, "log-scope")
            svc = next(
                a.value.string_value
                for a in recorded.resource.attributes
                if a.key == "service.name"
            )
            self.assertEqual(svc, "log-svc")
        provider.shutdown()

    def test_wait_for_log_record(self):
        provider = self._make_log_provider()
        logger = provider.get_logger("log-scope")
        logger.emit(body="wait-target", severity_number=SeverityNumber.INFO)

        found = self.server.wait_for_log_record(timeout=5.0)
        self.assertIsInstance(found, RecordedLogRecord)
        self.assertEqual(found.log_record.body.string_value, "wait-target")
        provider.shutdown()

    def test_log_drain_and_timeout(self):
        provider = self._make_log_provider()
        logger = provider.get_logger("log-scope")
        logger.emit(body="drain-me", severity_number=SeverityNumber.DEBUG)
        self.server.get_log_record(timeout=5.0)

        self.assertEqual(self.server.drain_log_records(), [])
        with self.assertRaises(TimeoutError):
            self.server.get_log_record(timeout=0.1)
        provider.shutdown()

    def test_compression(self):
        trace_provider = self._make_trace_provider(
            compression=Compression.Gzip
        )
        metrics_reader, metrics_provider = self._make_metrics_provider(
            compression=Compression.Gzip
        )
        log_provider = self._make_log_provider(compression=Compression.Gzip)

        trace_provider.get_tracer("s").start_span("gzip-span").end()
        self.assertEqual(
            self.server.get_span(timeout=5.0).span.name, "gzip-span"
        )

        metrics_provider.get_meter("s").create_counter("gzip.counter").add(1)
        metrics_reader.force_flush(timeout_millis=3000)
        self.assertEqual(
            self.server.get_metric(timeout=5.0).metric.name, "gzip.counter"
        )

        log_provider.get_logger("s").emit(
            body="gzip log", severity_number=SeverityNumber.INFO
        )
        self.assertEqual(
            self.server.get_log_record(
                timeout=5.0
            ).log_record.body.string_value,
            "gzip log",
        )

        trace_provider.shutdown()
        metrics_provider.shutdown()
        log_provider.shutdown()

    def test_endpoint_urls(self):
        port = self.server.port
        self.assertGreater(port, 0)
        self.assertEqual(
            self.server.traces_endpoint, f"http://127.0.0.1:{port}/v1/traces"
        )
        self.assertEqual(
            self.server.metrics_endpoint, f"http://127.0.0.1:{port}/v1/metrics"
        )
        self.assertEqual(
            self.server.logs_endpoint, f"http://127.0.0.1:{port}/v1/logs"
        )

    def test_context_manager(self):
        with OtlpProtoTestServer() as srv:
            provider = TracerProvider()
            provider.add_span_processor(
                SimpleSpanProcessor(
                    OTLPSpanExporter(endpoint=srv.traces_endpoint, timeout=1)
                )
            )
            provider.get_tracer("s").start_span("ctx-span").end()
            self.assertEqual(srv.get_span(timeout=5.0).span.name, "ctx-span")
            provider.shutdown()

    def test_base_path(self):
        with OtlpProtoTestServer(base_path="/custom") as srv:
            self.assertTrue(srv.traces_endpoint.endswith("/custom/v1/traces"))
            provider = TracerProvider()
            provider.add_span_processor(
                SimpleSpanProcessor(
                    OTLPSpanExporter(endpoint=srv.traces_endpoint, timeout=1)
                )
            )
            provider.get_tracer("s").start_span("prefixed-span").end()
            self.assertEqual(
                srv.get_span(timeout=5.0).span.name, "prefixed-span"
            )
            provider.shutdown()

    def test_signal_routing(self):
        trace_provider = self._make_trace_provider()
        metrics_reader, metrics_provider = self._make_metrics_provider()
        log_provider = self._make_log_provider()

        trace_provider.get_tracer("s").start_span("routed-span").end()
        metrics_provider.get_meter("s").create_counter("routed.counter").add(1)
        metrics_reader.force_flush(timeout_millis=3000)
        log_provider.get_logger("s").emit(
            body="routed log", severity_number=SeverityNumber.INFO
        )

        self.assertEqual(
            self.server.get_span(timeout=5.0).span.name, "routed-span"
        )
        self.assertEqual(
            self.server.get_metric(timeout=5.0).metric.name, "routed.counter"
        )
        self.assertEqual(
            self.server.get_log_record(
                timeout=5.0
            ).log_record.body.string_value,
            "routed log",
        )

        trace_provider.shutdown()
        metrics_provider.shutdown()
        log_provider.shutdown()

    def test_unknown_path_returns_404(self):
        resp = requests.post(
            f"http://127.0.0.1:{self.server.port}/unknown",
            data=b"",
            headers={"Content-Type": "application/x-protobuf"},
            timeout=2,
        )
        self.assertEqual(resp.status_code, 404)

    def test_missing_proto_raises_import_error(self):
        with unittest.mock.patch.dict(
            "sys.modules", {"opentelemetry.proto": None}
        ):
            with self.assertRaises(ImportError) as cm:
                OtlpProtoTestServer()
        self.assertIn("opentelemetry-proto", str(cm.exception))
