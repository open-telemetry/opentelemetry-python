OpenTelemetry Database API integration
=================================

The trace integration with Database API supports libraries following the specification.

.. PEP 249 -- Python Database API Specification v2.0: https://www.python.org/dev/peps/pep-0249/

Usage
-----

.. code:: python

    import mysql.connector
    from opentelemetry.trace import tracer_source
    from opentelemetry.ext.dbapi import trace_integration

    trace.set_preferred_tracer_source_implementation(lambda T: TracerSource())
    tracer = trace.get_tracer(__name__)
    # Ex: mysql.connector
    trace_integration(tracer_source(), mysql.connector, "connect", "mysql")


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
