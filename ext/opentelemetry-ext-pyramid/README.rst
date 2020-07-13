OpenTelemetry Pyramid Integration
=================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-ext-pyramid.svg
   :target: https://pypi.org/project/opentelemetry-ext-pyramid/

Installation
------------

::

    pip install opentelemetry-ext-pyramid

Exclude lists
*************
To exclude certain URLs from being tracked, set the environment variable ``OTEL_PYRAMID_EXCLUDED_URLS`` with comma delimited regexes representing which URLs to exclude.

For example, 

::

    export OTEL_PYRAMID_EXCLUDED_URLS="client/.*/info,healthcheck"

will exclude requests such as ``https://site/client/123/info`` and ``https://site/xyz/healthcheck``.

References
----------
* `OpenTelemetry Pyramid Integration <https://opentelemetry-python.readthedocs.io/en/latest/ext/pyramid/pyramid.html>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_

