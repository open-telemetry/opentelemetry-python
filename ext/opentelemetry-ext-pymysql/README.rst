OpenTelemetry PyMySQL integration
===============================

The integration with PyMySQL supports the `PyMySQL`_ library and is specified
to ``trace_integration`` using ``'PyMySQL'``.

.. _PyMySQL: https://pypi.org/project/PyMySQL/

Usage
-----

.. code:: python

    import pymysql
    from opentelemetry import trace
    from opentelemetry.ext.pymysql_ import trace_integration
    from opentelemetry.sdk.trace import TracerProvider

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    trace_integration(tracer)
    cnx = pymysql.connect(database='MySQL_Database')
    cursor = cnx.cursor()
    cursor.execute("INSERT INTO test (testField) VALUES (123)"
    cnx.commit()
    cursor.close()
    cnx.close()


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
