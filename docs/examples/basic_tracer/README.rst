Basic Trace
===========

These examples show how to use OpenTelemetry to create and export Spans.

There are two different examples:

* basic_trace: Shows how to configure a SpanProcessor and Exporter, and how to create a tracer and span.

* resources: Shows how to add resource information to a Provider. Note that this must be run on a Google Compute Engine instance.

The source files of these examples are available :scm_web:`here <docs/examples/basic_tracer/>`.

Installation
------------

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk

Run the Example
---------------

.. code-block:: sh

    python <example_name>.py

The output will be shown in the console.

Useful links
------------

- OpenTelemetry_
- :doc:`../../api/trace`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
