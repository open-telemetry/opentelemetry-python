OpenTelemetry Exporters HTTP Transport
======================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-exporter-http-transport.svg
   :target: https://pypi.org/project/opentelemetry-exporter-http-transport/

This package provides shared HTTP transport abstractions used by OpenTelemetry exporters.

The package has **no required dependencies**. The ``requests`` and ``urllib3``
transports are available as optional extras.

Installation
------------

Core package (no HTTP backend included)::

    pip install opentelemetry-exporter-http-transport

With the ``requests`` backend::

    pip install opentelemetry-exporter-http-transport[requests]

With the ``urllib3`` backend::

    pip install opentelemetry-exporter-http-transport[urllib3]

Proxies and CA bundles
----------------------

The ``urllib3`` transport is the default. It ignores the ``HTTP_PROXY``,
``HTTPS_PROXY``, ``ALL_PROXY``, ``NO_PROXY``, ``REQUESTS_CA_BUNDLE`` and
``CURL_CA_BUNDLE`` environment variables, which only ``requests`` honors. If
any of them is set, exporters use the ``requests`` transport instead. If
``requests`` is not installed, a warning is logged and the ``urllib3``
transport is used.


References
----------

* `OpenTelemetry <https://opentelemetry.io/>`_
* `OpenTelemetry Protocol Specification <https://github.com/open-telemetry/oteps/blob/main/text/0035-opentelemetry-protocol.md>`_
* `requests <https://requests.readthedocs.io>`_
* `urllib3 <https://urllib3.readthedocs.io>`_
