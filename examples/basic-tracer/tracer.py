import os

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.ext.jaeger import JaegerSpanExporter
from opentelemetry.sdk.trace import Tracer
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

trace.set_preferred_tracer_implementation(lambda T: Tracer())
tracer = trace.tracer()

if os.getenv("EXPORTER") == "jaeger":
    exporter = JaegerSpanExporter(
        service_name="basic-service",
        agent_host_name="localhost",
        agent_port=6831,
    )
else:
    exporter = ConsoleSpanExporter()

span_processor = BatchExportSpanProcessor(exporter)

tracer.add_span_processor(span_processor)
with tracer.start_as_current_span("foo"):
    with tracer.start_as_current_span("bar"):
        with tracer.start_as_current_span("baz"):
            print(Context)

span_processor.shutdown()
