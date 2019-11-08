OpenTelemetry WSGI Middleware
=============================

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-opentracing-wsgi.svg
   :target: https://pypi.org/project/opentelemetry-opentracing-wsgi/


This library provides a WSGI middleware that can be used on any WSGI framework
(such as Django / Flask) to track requests timing through OpenTelemetry.

Installation
------------

::

    pip install opentelemetry-opentracing-wsgi


Usage (Flask)
-------------

.. code-block:: python

    from flask import Flask
    from opentelemetry.ext.wsgi import OpenTelemetryMiddleware

    app = Flask(__name__)
    app.wsgi_app = OpenTelemetryMiddleware(app.wsgi_app)

    @app.route("/")
    def hello():
        return "Hello!"

    if __name__ == "__main__":
        app.run(debug=True)


Usage (Django)
--------------

Modify the application's ``wsgi.py`` file as shown below.

.. code-block:: python

    import os
    from opentelemetry.ext.wsgi import OpenTelemetryMiddleware
    from django.core.wsgi import get_wsgi_application

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')

    application = get_wsgi_application()
    application = OpenTelemetryMiddleware(application)

References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
* `WSGI <https://www.python.org/dev/peps/pep-3333>`_
