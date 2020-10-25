Basic Context
=============

These examples show how context is propagated through Spans in OpenTelemetry.

There are three different examples:

* implicit_context: Shows how starting a span implicitly creates context.

* child_context: Shows how context is propagated through child spans.

* async_context: Shows how context can be shared in another coroutine.

The source files of these examples are available :scm_web:`here <docs/examples/basic_context/>`.

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
