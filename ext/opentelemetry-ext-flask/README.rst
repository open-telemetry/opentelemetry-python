OpenTelemetry Flask tracing
===========================

This library builds on the OpenTelemetry WSGI middleware to track web requests
in Flask applications. In addition to opentelemetry-ext-wsgi, it supports
flask-specific features such as:

* The Flask endpoint name is used as the Span name.
* The ``http.route`` Span attribute is set so that one can see which URL rule matched a request.

Usage
-----

.. code-block:: python

    from flask import Flask
    from opentelemetry.ext.flask_util import instrument_app

    app = Flask(__name__)
    instrument_app(app)  # This is where the magic happens. ✨

    @app.route("/")
    def hello():
        return "Hello!"

    if __name__ == "__main__":
        app.run(debug=True)


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
* `OpenTelemetry WSGI extension <https://github.com/open-telemetry/opentelemetry-python/tree/master/ext/opentelemetry-ext-wsgi>`_
