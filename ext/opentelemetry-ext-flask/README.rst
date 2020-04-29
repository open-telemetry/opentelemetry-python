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

Blacklist
*********
Excludes certain hosts and paths from being tracked. Pass in comma delimited string into environment variables.

Blacklisted hosts: OPENTELEMETRY_PYTHON_FLASK_BLACKLIST_HOSTS
Blacklisted paths: OPENTELEMETRY_PYTHON_FLASK_BLACKLIST_PATHS


References
----------

* `OpenTelemetry Flask Tracing <https://opentelemetry-python.readthedocs.io/en/latest/ext/flask/flask.html>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
