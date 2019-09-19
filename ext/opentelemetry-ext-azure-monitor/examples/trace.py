from opentelemetry import trace
from opentelemetry.ext.azure_monitor import AzureMonitorSpanExporter
from opentelemetry.sdk.trace import Tracer
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

trace.set_preferred_tracer_implementation(lambda T: Tracer())
tracer = trace.tracer()
tracer.add_span_processor(SimpleExportSpanProcessor(AzureMonitorSpanExporter()))

with tracer.start_span('hello') as span:
    print('Hello, World!')
