OpenTelemetry Database API integration
======================================

The trace integration with Database API supports libraries following the specification.

.. PEP 249 -- Python Database API Specification v2.0: https://www.python.org/dev/peps/pep-0249/

Usage
-----

.. code-block:: python

    import mysql.connector
    from opentelemetry.trace import tracer_provider
    from opentelemetry.ext.dbapi import trace_integration

    trace.set_preferred_tracer_provider_implementation(lambda T: TracerProvider())
    tracer = trace.get_tracer(__name__)
    # Ex: mysql.connector
    trace_integration(tracer_provider(), mysql.connector, "connect", "mysql")


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
