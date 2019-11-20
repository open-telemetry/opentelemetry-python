OpenTelemetry Database API integration
=================================

The trace integration with Database API supports libraries following the specification.

.. PEP 249 -- Python Database API Specification v2.0: https://www.python.org/dev/peps/pep-0249/

Usage
-----

.. code:: python

    import wrapt
    import mysql.connector
    from opentelemetry.trace import tracer
    from opentelemetry.ext.dbapi import trace_integration


    # Ex: mysql.connector
    trace_integration(tracer(), mysql.connector, "connect", "mysql")


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
