from opentelemetry import trace
from opentelemetry.sdk.trace import Tracer, TracerProvider
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


class TracerTestBase:
    @classmethod
    def setUpClass(cls):
        # pylint: disable=invalid-name
        cls._tracer_provider = TracerProvider()
        trace.set_tracer_provider(cls._tracer_provider)
        cls._tracer = Tracer(cls._tracer_provider, None)
        cls._span_exporter = InMemorySpanExporter()
        cls._span_processor = SimpleExportSpanProcessor(cls._span_exporter)
        cls._tracer_provider.add_span_processor(cls._span_processor)

    def pop_traces(self):
        spans = self._span_exporter.get_finished_spans()
        return spans
