import unittest
from importlib import reload

from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider, export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

_MEMORY_EXPORTER = None


class SpanTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global _MEMORY_EXPORTER  # pylint:disable=global-statement
        trace_api.set_tracer_provider(TracerProvider())
        tracer_provider = trace_api.get_tracer_provider()
        _MEMORY_EXPORTER = InMemorySpanExporter()
        span_processor = export.SimpleExportSpanProcessor(_MEMORY_EXPORTER)
        tracer_provider.add_span_processor(span_processor)

    @classmethod
    def tearDownClass(cls):
        reload(trace_api)

    def setUp(self):
        self.memory_exporter = _MEMORY_EXPORTER
        self.memory_exporter.clear()
