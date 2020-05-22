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
Excludes certain hosts and paths from being tracked. Pass in comma delimited string into environment variables.
Host refers to the entire url and path refers to the part of the url after the domain. Host matches the exact string that is given, where as path matches if the url starts with the given excluded path.

Excluded hosts: OPENTELEMETRY_PYTHON_FLASK_EXCLUDED_HOSTS
Excluded paths: OPENTELEMETRY_PYTHON_FLASK_EXCLUDED_PATHS


References
----------

* `OpenTelemetry Flask Tracing <https://opentelemetry-python.readthedocs.io/en/latest/ext/flask/flask.html>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
