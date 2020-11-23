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
