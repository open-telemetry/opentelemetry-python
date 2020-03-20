OpenTelemetry Database API integration
======================================

The trace integration with Database API supports libraries following the specification.

.. PEP 249 -- Python Database API Specification v2.0: https://www.python.org/dev/peps/pep-0249/

Usage
-----

.. code-block:: python

    import mysql.connector
    import pyodbc

    from opentelemetry.ext.dbapi import trace_integration
    from opentelemetry.sdk.trace import TracerProvider

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    # Ex: mysql.connector
    trace_integration(tracer, mysql.connector, "connect", "mysql", "sql")
    # Ex: pyodbc
    trace_integration(tracer, pyodbc, "Connection", "odbc", "sql")


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
