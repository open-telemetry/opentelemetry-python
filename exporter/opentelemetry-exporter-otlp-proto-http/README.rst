OpenTelemetry Collector Protobuf over HTTP Exporter
===================================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-exporter-otlp-proto-http.svg
   :target: https://pypi.org/project/opentelemetry-exporter-otlp-proto-http/

This library allows to export data to the OpenTelemetry Collector using the OpenTelemetry Protocol using Protobuf over HTTP.

Installation
------------

::

     pip install opentelemetry-exporter-otlp-proto-http

To use a custom ``requests.Session`` (for example to configure authentication), pass it to the exporter:

.. code-block:: python

     import requests
     from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

     exporter = OTLPSpanExporter(session=requests.Session())


References
----------

* `OpenTelemetry Collector Exporter <https://opentelemetry-python.readthedocs.io/en/latest/exporter/otlp/otlp.html>`_
* `OpenTelemetry Collector <https://github.com/open-telemetry/opentelemetry-collector/>`_
* `OpenTelemetry <https://opentelemetry.io/>`_
* `OpenTelemetry Protocol Specification <https://github.com/open-telemetry/oteps/blob/main/text/0035-opentelemetry-protocol.md>`_
