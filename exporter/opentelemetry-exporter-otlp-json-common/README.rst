OpenTelemetry JSON Encoding
===========================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-exporter-otlp-json-common.svg
   :target: https://pypi.org/project/opentelemetry-exporter-otlp-json-common/

This library is provided as a convenience to encode to JSON format for OTLP. Currently used by:

* opentelemetry-exporter-otlp-json-http
* (Future) opentelemetry-exporter-otlp-json-grpc

This package provides JSON encoding for OpenTelemetry's traces, metrics, and logs, which is required by some collectors and observability platforms like Langfuse.

Installation
------------

::

     pip install opentelemetry-exporter-otlp-json-common


References
----------

* `OpenTelemetry <https://opentelemetry.io/>`_
* `OpenTelemetry Protocol Specification <https://github.com/open-telemetry/oteps/blob/main/text/0035-opentelemetry-protocol.md>`_