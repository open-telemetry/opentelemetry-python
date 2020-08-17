from opentelemetry import trace
from opentelemetry.sdk.resources import get_aggregated_resources
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)
from opentelemetry.tools.resource_detector import GoogleCloudResourceDetector

resources = get_aggregated_resources([GoogleCloudResourceDetector()])

trace.set_tracer_provider(TracerProvider(resource=resources))

trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(ConsoleSpanExporter())
)
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("foo"):
    print("Hello world!")
