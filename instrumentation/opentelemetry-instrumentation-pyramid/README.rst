OpenTelemetry Pyramid Integration
=================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-instrumentation-pyramid.svg
   :target: https://pypi.org/project/opentelemetry-instrumentation-pyramid/

Installation
------------

::

    pip install opentelemetry-instrumentation-pyramid

Exclude lists
*************
To exclude certain URLs from being tracked, set the environment variable ``OPENTELEMETRY_PYTHON_PYRAMID_EXCLUDED_URLS`` with comma delimited regexes representing which URLs to exclude.

For example, 

::

    export OPENTELEMETRY_PYTHON_PYRAMID_EXCLUDED_URLS="client/.*/info,healthcheck"

will exclude requests such as ``https://site/client/123/info`` and ``https://site/xyz/healthcheck``.

References
----------
* `OpenTelemetry Pyramid Integration <https://opentelemetry-python.readthedocs.io/en/latest/ext/pyramid/pyramid.html>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_

