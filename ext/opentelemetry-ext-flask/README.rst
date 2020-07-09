OpenTelemetry Flask Tracing
===========================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-ext-flask.svg
   :target: https://pypi.org/project/opentelemetry-ext-flask/

This library builds on the OpenTelemetry WSGI middleware to track web requests
in Flask applications.

Installation
------------

::

    pip install opentelemetry-ext-flask

Configuration
-------------

Exclude lists
*************
To exclude certain URLs from being tracked, set the environment variable ``OPENTELEMETRY_PYTHON_FLASK_EXCLUDED_URLS`` with comma delimited regexes representing which URLs to exclude.

For example,

::

    export OPENTELEMETRY_PYTHON_FLASK_EXCLUDED_URLS="client/.*/info,healthcheck"

will exclude requests such as ``https://site/client/123/info`` and ``https://site/xyz/healthcheck``.

References
----------

* `OpenTelemetry Flask Tracing <https://opentelemetry-python.readthedocs.io/en/latest/ext/flask/flask.html>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
