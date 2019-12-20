#!/usr/bin/env python

from opentelemetry import trace
from opentelemetry.ext import opentracing_shim
from opentelemetry.ext.jaeger import JaegerSpanExporter
from opentelemetry.sdk.trace import TracerSource
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor
from rediscache import RedisCache

# Configure the tracer using the default implementation
trace.set_preferred_tracer_source_implementation(lambda T: TracerSource())
tracer = trace.tracer_source().get_tracer(__name__)

# Configure the tracer to export traces to Jaeger
jaeger_exporter = JaegerSpanExporter(
    service_name="OpenTracing Shim Example",
    agent_host_name="localhost",
    agent_port=6831,
)
span_processor = BatchExportSpanProcessor(jaeger_exporter)
trace.tracer_source().add_span_processor(span_processor)

# Create an OpenTracing shim. This implements the OpenTracing tracer API, but
# forwards calls to the underlying OpenTelemetry tracer.
opentracing_tracer = opentracing_shim.create_tracer(tracer)

# Our example caching library expects an OpenTracing-compliant tracer.
redis_cache = RedisCache(opentracing_tracer)


@redis_cache
def fib(n):
    """Get the Nth Fibonacci number, cache intermediate results in Redis."""
    if n < 0:
        raise ValueError
    if n == 0 or n == 1:
        return n
    return fib(n - 1) + fib(n - 2)


with tracer.start_as_current_span("Fibonacci") as span:
    span.set_attribute("is_example", "yes :)")
    fib(4)


# Export the remaining span before exiting
span_processor.shutdown()
