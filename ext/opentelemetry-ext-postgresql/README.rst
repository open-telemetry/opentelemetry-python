OpenTelemetry PostgreSQL integration
=================================

The integration with PostgreSQL supports the `Psycopg`_ library and is specified
to ``trace_integration`` using ``'PostgreSQL'``.

.. Psycopg: http://initd.org/psycopg/

Usage
-----

.. code:: python
    import psycopg2
    from opentelemetry.trace import tracer
    from opentelemetry.trace.ext.postgresql import trace_integration
    trace_integration(tracer())
    cnx = psycopg2.connect(database='Database')
    cursor = cnx.cursor()
    cursor.execute("INSERT INTO test (testField) VALUES (123)"
    cursor.close()
    cnx.close()

References
----------
* `OpenTelemetry Project <https://opentelemetry.io/>`_