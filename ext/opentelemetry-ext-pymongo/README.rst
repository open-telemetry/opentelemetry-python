OpenTelemetry pymongo integration
=================================

The integration with MongoDB supports the `pymongo`_ library and is specified
to ``trace_integrations`` using ``'pymongo'``.

.. _pymongo: https://pypi.org/project/pymongo

Usage
-----

.. code:: python

    from opencensus.trace import config_integration

    config_integration.trace_integrations(['pymongo'])

References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
