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
Excludes certain hosts and paths from being tracked. Pass in comma delimited string into environment variables.
Host refers to the entire url and path refers to the part of the url after the domain. Host matches the exact string that is given, where as path matches if the url starts with the given excluded path.

Excluded hosts: OPENTELEMETRY_PYTHON_DJANGO_EXCLUDED_HOSTS
Excluded paths: OPENTELEMETRY_PYTHON_DJANGO_EXCLUDED_PATHS

References
----------

* `Django <https://www.djangoproject.com/>`_
* `OpenTelemetry Django Tracing <https://opentelemetry-python.readthedocs.io/en/latest/ext/django/django.html>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
