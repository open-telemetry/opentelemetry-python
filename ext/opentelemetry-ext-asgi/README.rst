OpenTelemetry ASGI Middleware
=============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-ext-asgi.svg
   :target: https://pypi.org/project/opentelemetry-ext-asgi/


This library provides a ASGI middleware that can be used on any ASGI framework
(such as Django, Starlette, FastAPI or Quart) to track requests timing through OpenTelemetry.

Installation
------------

::

    pip install opentelemetry-ext-asgi


Usage (Quart)
-------------

.. code-block:: python

    from quart import Quart
    from opentelemetry.ext.asgi import OpenTelemetryMiddleware

    app = Quart(__name__)
    app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)

    @app.route("/")
    async def hello():
        return "Hello!"

    if __name__ == "__main__":
        app.run(debug=True)


Usage (Django)
--------------

Modify the application's ``asgi.py`` file as shown below.

.. code-block:: python

    import os
    import django
    from channels.routing import get_default_application
    from opentelemetry.ext.asgi import OpenTelemetryMiddleware

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
    django.setup()

    application = get_default_application()
    application = OpenTelemetryMiddleware(application)

References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
