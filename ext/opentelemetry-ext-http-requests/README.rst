OpenTelemetry requests integration
==================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-ext-http-requests.svg
   :target: https://pypi.org/project/opentelemetry-ext-http-requests/

This library allows tracing HTTP requests made by the popular `requests <https://requests.kennethreitz.org/en/master/>`_ library.

Installation
------------

::

     pip install opentelemetry-ext-http-requests

Usage
-----

.. code-block:: python

    import requests
    import opentelemetry.ext.http_requests
    from opentelemetry.trace import tracer_provider

    opentelemetry.ext.http_requests.enable(tracer_provider())
    response = requests.get(url='https://www.example.org/')

Limitations
-----------

Note that calls that do not use the higher-level APIs but use
:code:`requests.sessions.Session.send` (or an alias thereof) directly, are
currently not traced. If you find any other way to trigger an untraced HTTP
request, please report it via a GitHub issue with :code:`[requests: untraced
API]` in the title.

References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
