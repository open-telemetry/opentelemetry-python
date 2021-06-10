Frequently Asked Questions and Cookbook
=======================================

This page answers frequently asked questions, and serves as a cookbook
for common scenarios.

Create a new span
-----------------

.. code-block:: python

    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("print") as span:
        print("foo")
        span.set_attribute("printed_string", "foo")

Getting and modifying a span
----------------------------

.. code-block:: python

    from opentelemetry import trace

    current_span = trace.get_current_span()
    current_span.set_attribute("hometown", "seattle")

Capturing baggage at different contexts
---------------------------------------

.. code-block:: python

    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(name="root span") as root_span:
        parent_ctx = baggage.set_baggage("context", "parent")
        with tracer.start_as_current_span(
            name="child span", context=parent_ctx
        ) as child_span:
            child_ctx = baggage.set_baggage("context", "child")

    print(baggage.get_baggage("context", parent_ctx))
    print(baggage.get_baggage("context", child_ctx))

Manually setting span context
-----------------------------

.. code-block:: python

    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    from opentelemetry import trace
    from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    tracer = trace.get_tracer(__name__)

    # Extracting from carrier header
    carrier = {'traceparent': '00-a9c3b99a95cc045e573e163c3ac80a77-d99d251a8caecd06-01'}
    ctx = TraceContextTextMapPropagator().extract(carrier=carrier)

    with tracer.start_as_current_span('child', context=ctx) as span:
        span.set_attribute('primes', [2, 3, 5, 7])

    # Or if you have a SpanContext object already.
    span_context = SpanContext(
        trace_id=2604504634922341076776623263868986797,
        span_id=5213367945872657620,
        is_remote=True,
        trace_flags=TraceFlags(0x01)
    )
    ctx = trace.set_span_in_context(NonRecordingSpan(span_context))

    with tracer.start_as_current_span("child", context=ctx) as span:
        span.set_attribute('evens', [2, 4, 6, 8])

Using multiple tracer providers with different Resource
-------------------------------------------------------

.. code-block:: python

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace.export import (ConsoleSpanExporter,
                                                SimpleSpanProcessor)

    # Global tracer provider which can be set only once
    trace.set_tracer_provider(
        TracerProvider(resource=Resource.create({"service.name": "service1"}))
    )
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("some-name") as span:
        span.set_attribute("key", "value")



    another_tracer_provider = TracerProvider(
        resource=Resource.create({"service.name": "service2"})
    )
    another_tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    another_tracer = trace.get_tracer(__name__, tracer_provider=another_tracer_provider)
    with another_tracer.start_as_current_span("name-here") as span:
        span.set_attribute("another-key", "another-value")
