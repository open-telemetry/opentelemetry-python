OpenTelemetry Zipkin Exporter
=============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-exporter-zipkin.svg
   :target: https://pypi.org/project/opentelemetry-exporter-zipkin/

This library is provided as a convenience to install all supported OpenTelemetry Zipkin Exporters. Currently it installs:
* opentelemetry-exporter-zipkin-json
* opentelemetry-exporter-zipkin-proto-http

In the future, additional packages may be available:
* opentelemetry-exporter-zipkin-thrift

To avoid unnecessary dependencies, users should install the specific package once they've determined their
preferred serialization method.

Installation
------------

::

     pip install opentelemetry-exporter-zipkin


References
----------

* `OpenTelemetry Zipkin Exporter <https://opentelemetry-python.readthedocs.io/en/latest/exporter/zipkin/zipkin.html>`_
* `Zipkin <https://zipkin.io/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
