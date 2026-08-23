# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""`bytes` is a valid attribute value type, so a Resource carrying one must
stay hashable and serialisable.

Every OTLP encoder groups telemetry by using the Resource as a dict key, so a
Resource that cannot be hashed takes the whole export path down with it.
"""

import json
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


class TestResourceWithBytesAttribute(unittest.TestCase):
    def setUp(self):
        self.resource = Resource.create(_BYTES_RESOURCE)

    def test_resource_is_hashable(self):
        hash(self.resource)

    def test_resource_usable_as_dict_key(self):
        """OTLP encoders group telemetry by Resource identity."""
        self.assertEqual({self.resource: "value"}[self.resource], "value")

    def test_resource_to_json_is_valid_json(self):
        payload = json.loads(self.resource.to_json())
        self.assertEqual(payload["attributes"]["build.id"], "010203")

    def test_equal_resources_hash_equally(self):
        self.assertEqual(hash(self.resource), hash(Resource.create(dict(_BYTES_RESOURCE))))

    def test_differing_bytes_hash_differently(self):
        other = Resource.create({"service.name": "svc", "build.id": b"\xff"})
        self.assertNotEqual(hash(self.resource), hash(other))

    def test_bytes_and_equivalent_string_are_distinct(self):
        """The hash fallback must not make b"\\x01\\x02\\x03" collide with "010203"."""
        as_text = Resource.create({"service.name": "svc", "build.id": "010203"})
        self.assertNotEqual(self.resource, as_text)


class TestBytesResourceExports(unittest.TestCase):
    """The full export path for each signal must survive a bytes resource."""

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
