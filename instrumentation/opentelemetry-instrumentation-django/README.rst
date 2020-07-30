OpenTelemetry Django Tracing
============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-ext-django.svg
   :target: https://pypi.org/project/opentelemetry-ext-django/

This library allows tracing requests for Django applications.

Installation
------------

::

    pip install opentelemetry-ext-django

Configuration
-------------

Exclude lists
*************
To exclude certain URLs from being tracked, set the environment variable ``OPENTELEMETRY_PYTHON_DJANGO_EXCLUDED_URLS`` with comma delimited regexes representing which URLs to exclude.

For example,

::

    export OPENTELEMETRY_PYTHON_DJANGO_EXCLUDED_URLS="client/.*/info,healthcheck"

will exclude requests such as ``https://site/client/123/info`` and ``https://site/xyz/healthcheck``.

References
----------

* `Django <https://www.djangoproject.com/>`_
* `OpenTelemetry Django Tracing <https://opentelemetry-python.readthedocs.io/en/latest/ext/django/django.html>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
