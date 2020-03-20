OpenTelemetry pymongo integration
=================================

The integration with MongoDB supports the `pymongo`_ library and is specified
to ``trace_integration`` using ``'pymongo'``.

.. _pymongo: https://pypi.org/project/pymongo

Usage
-----

.. code:: python

    from pymongo import MongoClient
    from opentelemetry.trace import TracerProvider

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    trace_integration(tracer)
    client = MongoClient()
    db = client["MongoDB_Database"]
    collection = db["MongoDB_Collection"]
    collection.find_one()

References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
