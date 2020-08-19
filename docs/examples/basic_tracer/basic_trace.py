from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)
from opentelemetry.trace.sampling import ProbabilitySampler, ALWAYS_OFF, ALWAYS_ON

tracer_provider = TracerProvider(sampler=ProbabilitySampler(0.2))
trace.set_tracer_provider(tracer_provider)
trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(ConsoleSpanExporter())
)
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("outer"):
    with tracer.start_as_current_span("inner"):
        print("Hello world!")
