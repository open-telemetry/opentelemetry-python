OpenTelemetry Database API integration
=================================

The trace integration with Database API supports libraries following the specification.

.. PEP 249 -- Python Database API Specification v2.0: https://www.python.org/dev/peps/pep-0249/

Usage
-----

.. code:: python

    import wrapt
    from opentelemetry.trace import tracer
    from opentelemetry.trace.ext.dbapi import DatabaseApiTracer

    def wrap(
        wrapped: typing.Callable[..., any],
        instance: typing.Any,
        args: typing.Tuple[any, any],
        kwargs: typing.Dict[any, any],
    ):
        """Patch MySQL Connector connect method to add tracing.
        """
        mysql_tracer = DatabaseApiTracer(tracer, "mysql")
        return mysql_tracer.wrap_connect(wrapped, args, kwargs)

    # Ex: mysql.connector
    wrapt.wrap_function_wrapper(mysql.connector, "connect", wrap)


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
