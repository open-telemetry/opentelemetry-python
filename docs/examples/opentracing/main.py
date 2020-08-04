#!/usr/bin/env python

from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerSpanExporter
from opentelemetry.instrumentation import opentracing_shim
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
from rediscache import RedisCache

# Configure the tracer using the default implementation
trace.set_tracer_provider(TracerProvider())
tracer_provider = trace.get_tracer_provider()

# Configure the tracer to export traces to Jaeger
jaeger_exporter = JaegerSpanExporter(
    service_name="OpenTracing Shim Example",
    agent_host_name="localhost",
    agent_port=6831,
)
span_processor = SimpleExportSpanProcessor(jaeger_exporter)
tracer_provider.add_span_processor(span_processor)

# Create an OpenTracing shim. This implements the OpenTracing tracer API, but
# forwards calls to the underlying OpenTelemetry tracer.
opentracing_tracer = opentracing_shim.create_tracer(tracer_provider)

# Our example caching library expects an OpenTracing-compliant tracer.
redis_cache = RedisCache(opentracing_tracer)

# Appication code uses an OpenTelemetry Tracer as usual.
tracer = trace.get_tracer(__name__)


@redis_cache
def fib(number):
    """Get the Nth Fibonacci number, cache intermediate results in Redis."""
    if number < 0:
        raise ValueError
    if number in (0, 1):
        return number
    return fib(number - 1) + fib(number - 2)


with tracer.start_as_current_span("Fibonacci") as span:
    span.set_attribute("is_example", "yes :)")
    fib(4)
