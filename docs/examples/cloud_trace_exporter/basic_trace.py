from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

trace.set_tracer_provider(TracerProvider())

cloud_trace_exporter = CloudTraceSpanExporter()
trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(cloud_trace_exporter)
)
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("foo") as span:
    value = 'a' * 256
    span.set_attribute('key', value)
    print("Hello world!")
