import io
import unittest
import wsgiref.util as wsgiref_util
from importlib import reload

from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerSource, export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

_MEMORY_EXPORTER = None


class WsgiTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global _MEMORY_EXPORTER
        trace_api.set_preferred_tracer_source_implementation(
            lambda T: TracerSource()
        )
        tracer_source = trace_api.tracer_source()
        _MEMORY_EXPORTER = InMemorySpanExporter()
        span_processor = export.SimpleExportSpanProcessor(_MEMORY_EXPORTER)
        tracer_source.add_span_processor(span_processor)

    @classmethod
    def tearDownClass(cls):
        reload(trace_api)

    def setUp(self):

        self.memory_exporter = _MEMORY_EXPORTER
        self.memory_exporter.clear()

        self.write_buffer = io.BytesIO()
        self.write = self.write_buffer.write

        self.environ = {}
        wsgiref_util.setup_testing_defaults(self.environ)

        self.status = None
        self.response_headers = None
        self.exc_info = None

    def start_response(self, status, response_headers, exc_info=None):
        self.status = status
        self.response_headers = response_headers
        self.exc_info = exc_info
        return self.write
