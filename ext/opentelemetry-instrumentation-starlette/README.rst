OpenTelemetry ASGI Middleware
=============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-instrumentation-starlette.svg
   :target: https://pypi.org/project/opentelemetry-instrumentation-starlette/


This library provides a ASGI middleware that can be used on any ASGI framework
(such as Django, Starlette, FastAPI or Quart) to track requests timing through OpenTelemetry.

Installation
------------

::

    pip install opentelemetry-instrumentation-starlette


Usage (Quart)
-------------

.. code-block:: python

    from quart import Quart
    from opentelemetry.instrumentation.starlette import OpenTelemetryMiddleware

    app = Quart(__name__)
    app.starlette_app = OpenTelemetryMiddleware(app.starlette_app)

    @app.route("/")
    async def hello():
        return "Hello!"

    if __name__ == "__main__":
        app.run(debug=True)


Usage (Django 3.0)
------------------

Modify the application's ``starlette.py`` file as shown below.

.. code-block:: python

    import os
    from django.core.starlette import get_starlette_application
    from opentelemetry.instrumentation.starlette import OpenTelemetryMiddleware

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'starlette_example.settings')

    application = get_starlette_application()
    application = OpenTelemetryMiddleware(application)


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
