import time

import opentelemetry.ext.jaeger as exporter
from opentelemetry.sdk import trace
from opentelemetry.sdk.trace import export

tracer = trace.tracer

# Create a JaegerSpanExporter
jaeger_exporter = exporter.JaegerSpanExporter()

# Create a SimpleExportSpanProcessor and add the exporter to it
span_processor = export.SimpleExportSpanProcessor(jaeger_exporter)

# add to the tracer
tracer.add_span_processor(span_processor)

# create some spans for testing
with tracer.start_span("foo") as foo:
    time.sleep(0.1)
    foo.set_attribute("my_atribbute", True)
    foo.add_event("event in foo", {"name": "foo1"})
    with tracer.start_span("bar") as bar:
        time.sleep(0.2)
        bar.set_attribute("speed", 100.0)
        bar.add_link(foo.get_context())

        with tracer.start_span("baz") as baz:
            time.sleep(0.3)
            baz.set_attribute("name", "mauricio")

        time.sleep(0.2)

    time.sleep(0.1)
