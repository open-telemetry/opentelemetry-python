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

Proxies
-------

Both transports pick up proxies from the environment the same way ``requests``
does: ``HTTP_PROXY``, ``HTTPS_PROXY``, ``ALL_PROXY`` and ``NO_PROXY`` (lowercase
variants take precedence), falling back to the system proxy settings on macOS
and Windows. Credentials in the proxy URL are used for proxy authentication.

SOCKS proxies (``socks4://``, ``socks4a://``, ``socks5://``, ``socks5h://``)
require `PySocks <https://pypi.org/project/PySocks/>`_::

    pip install urllib3[socks]


References
----------

* `OpenTelemetry <https://opentelemetry.io/>`_
* `OpenTelemetry Protocol Specification <https://github.com/open-telemetry/oteps/blob/main/text/0035-opentelemetry-protocol.md>`_
* `requests <https://requests.readthedocs.io>`_
* `urllib3 <https://urllib3.readthedocs.io>`_
