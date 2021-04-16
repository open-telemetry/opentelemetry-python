import time

from opentelemetry import trace
from opentelemetry.exporter.jaeger.proto import grpc
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Create a JaegerExporter to send spans with gRPC
# If there is no encryption or authentication set `insecure` to True
# If server has authentication with SSL/TLS you can set the
# parameter credentials=ChannelCredentials(...) or the environment variable
# `EXPORTER_JAEGER_CERTIFICATE` with file containing creds.

jaeger_exporter = grpc.JaegerExporter(
    collector_endpoint="localhost:14250",
    insecure=True,
)

# create a BatchSpanProcessor and add the exporter to it
span_processor = BatchSpanProcessor(jaeger_exporter)

# add to the tracer factory
trace.get_tracer_provider().add_span_processor(span_processor)

# create some spans for testing
with tracer.start_as_current_span("foo") as foo:
    time.sleep(0.1)
    foo.set_attribute("my_atribbute", True)
    foo.add_event("event in foo", {"name": "foo1"})
    with tracer.start_as_current_span(
        "bar", links=[trace.Link(foo.get_span_context())]
    ) as bar:
        time.sleep(0.2)
        bar.set_attribute("speed", 100.0)

        with tracer.start_as_current_span("baz") as baz:
            time.sleep(0.3)
            baz.set_attribute("name", "mauricio")

        time.sleep(0.2)

    time.sleep(0.1)
