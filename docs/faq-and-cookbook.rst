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
