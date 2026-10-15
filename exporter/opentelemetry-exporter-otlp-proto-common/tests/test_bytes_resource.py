# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Every OTLP encoder groups telemetry by using the Resource as a dict key, so
a Resource carrying a bytes attribute must survive the whole export path.
"""

import unittest

from opentelemetry.exporter.otlp.proto.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    InMemoryLogExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

_BYTES_RESOURCE = {"service.name": "svc", "build.id": b"\x01\x02\x03"}


class TestBytesResourceExports(unittest.TestCase):
    def setUp(self):
        self.resource = Resource.create(_BYTES_RESOURCE)

    def test_encode_spans(self):
        exporter = InMemorySpanExporter()
        provider = TracerProvider(resource=self.resource, shutdown_on_exit=False)
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        with provider.get_tracer(__name__).start_as_current_span("span"):
            pass
        request = encode_spans(exporter.get_finished_spans())
        self.assertEqual(len(request.resource_spans), 1)
        provider.shutdown()

    def test_encode_metrics(self):
        reader = InMemoryMetricReader()
        provider = MeterProvider(metric_readers=[reader], resource=self.resource)
        provider.get_meter(__name__).create_counter("counter").add(1)
        request = encode_metrics(reader.get_metrics_data())
        self.assertEqual(len(request.resource_metrics), 1)
        provider.shutdown()

    def test_encode_logs(self):
        exporter = InMemoryLogExporter()
        provider = LoggerProvider(resource=self.resource, shutdown_on_exit=False)
        provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
        provider.get_logger(__name__).emit(body="body")
        request = encode_logs(exporter.get_finished_logs())
        self.assertEqual(len(request.resource_logs), 1)
        provider.shutdown()
