OpenTelemetry Jaeger Exporter
=============================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-exporter-jaeger.svg
   :target: https://pypi.org/project/opentelemetry-exporter-jaeger/

This library is provided as a convenience to install all supported Jaeger Exporters. Currently it installs:
* opentelemetry-exporter-jaeger-proto-grpc
* opentelemetry-exporter-jaeger-thrift

To avoid unnecessary dependencies, users should install the specific package once they've determined their
preferred serialization method.

Installation
------------

::

    pip install opentelemetry-exporter-jaeger


References
----------

* `OpenTelemetry Jaeger Exporter <https://opentelemetry-python.readthedocs.io/en/latest/exporter/jaeger/jaeger.html>`_
* `Jaeger <https://www.jaegertracing.io/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
