OpenTelemetry FastAPI Instrumentation
=====================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-instrumentation-fastapi.svg
   :target: https://pypi.org/project/opentelemetry-instrumentation-fastapi/


This library provides automatic and manual instrumentation of the FastAPI web framework,
instrumenting http requests served by applications utilizing the framework.

auto-instrumentation using the opentelemetry-instrumentation package is also supported.

Installation
------------

::

    pip install opentelemetry-instrumentation-fastapi


Usage
-----

.. code-block:: python

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    import fastapi

    app = fastapi.FastAPI()

    @app.route("/")
    def home():
        return {}

    FastAPIInstrumentor.instrument_app(app)


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_