OpenTelemetry Psycopg integration
=================================

The integration with PostgreSQL supports the `Psycopg`_ library and is specified
to ``trace_integration`` using ``'PostgreSQL'``.

.. _Psycopg: http://initd.org/psycopg/

Usage
-----

.. code-block:: python

    import psycopg2
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.ext.psycopg2 import trace_integration

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    trace_integration(tracer)
    cnx = psycopg2.connect(database='Database')
    cursor = cnx.cursor()
    cursor.execute("INSERT INTO test (testField) VALUES (123)")
    cursor.close()
    cnx.close()

References
----------
* `OpenTelemetry Project <https://opentelemetry.io/>`_
