OpenTelemetry requests integration
==================================

This library allows tracing HTTP requests made by the popular `requests <(https://2.python-requests.org//en/latest/>` library.

Usage
-----

.. code-block:: python

    import requests
    from opentelemetry.ext.requests import enable as enable_requests_integration
    from opentelemetry.trace import tracer

    enable_requests_integration(tracer())
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
