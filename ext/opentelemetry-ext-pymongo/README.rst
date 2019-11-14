OpenTelemetry pymongo integration
=================================

The integration with MongoDB supports the `pymongo`_ library and is specified
to ``trace_integration`` using ``'pymongo'``.

.. _pymongo: https://pypi.org/project/pymongo

Usage
-----

.. code:: python

    from pymongo import MongoClient
    from opentelemetry.trace import tracer
    from opentelemetry.trace.ext.pymongo import trace_integration

    trace_integration(tracer())
    client = MongoClient()
    db = client["MongoDB_Database"]
    collection = db["MongoDB_Collection"]
    collection.find_one()

References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
