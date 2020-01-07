OpenTelemetry MySQL integration
=================================

The integration with MySQL supports the `mysql-connector`_ library and is specified
to ``trace_integration`` using ``'MySQL'``.

.. mysql-connector: https://pypi.org/project/mysql-connector/

Usage
-----

.. code:: python

    import mysql.connector
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerSource
    from opentelemetry.ext.mysql import trace_integration

    trace.set_preferred_tracer_source_implementation(lambda T: TracerSource())
    tracer = trace.tracer_source().get_tracer(__name__)
    trace_integration(tracer)
    cnx = mysql.connector.connect(database='MySQL_Database')
    cursor = cnx.cursor()
    cursor.execute("INSERT INTO test (testField) VALUES (123)"
    cursor.close()
    cnx.close()


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
