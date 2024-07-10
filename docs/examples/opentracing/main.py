#!/usr/bin/env python

from rediscache import RedisCache

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.shim import opentracing_shim

# Configure the tracer using the default implementation
trace.set_tracer_provider(TracerProvider())
tracer_provider = trace.get_tracer_provider()

# Create an OTLP gRPC span exporter
otlp_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4317",
    # For insecure connection, useful for testing
    insecure=True,
)
# Add the exporter to the tracer provider
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# Create an OpenTracing shim. This implements the OpenTracing tracer API, but
# forwards calls to the underlying OpenTelemetry tracer.
opentracing_tracer = opentracing_shim.create_tracer(tracer_provider)

# Our example caching library expects an OpenTracing-compliant tracer.
redis_cache = RedisCache(opentracing_tracer)

# Application code uses an OpenTelemetry Tracer as usual.
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
