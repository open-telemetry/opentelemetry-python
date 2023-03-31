OpenTelemetry Jaeger Protobuf Exporter
======================================

.. warning::
    Since v1.35, the Jaeger supports OTLP natively. Please use the OTLP exporter instead.
    Support for this exporter will end July 2023.

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-exporter-jaeger-proto-grpc.svg
   :target: https://pypi.org/project/opentelemetry-exporter-jaeger-proto-grpc/

This library allows to export tracing data to `Jaeger <https://www.jaegertracing.io/>`_.

Installation
------------

::

    pip install opentelemetry-exporter-jaeger-proto-grpc


.. _Jaeger: https://www.jaegertracing.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/

Configuration
-------------

OpenTelemetry Jaeger Exporter can be configured by setting `JaegerExporter parameters
<https://github.com/open-telemetry/opentelemetry-python/blob/main/exporter/opentelemetry-exporter-jaeger-proto-grpc
/src/opentelemetry/exporter/jaeger/proto/__init__.py#L88>`_ or by setting
`environment variables <https://github.com/open-telemetry/opentelemetry-specification/blob/main/
specification/sdk-environment-variables.md#jaeger-exporter>`_

References
----------

* `OpenTelemetry Jaeger Exporter <https://opentelemetry-python.readthedocs.io/en/latest/exporter/jaeger/jaeger.html>`_
* `Jaeger <https://www.jaegertracing.io/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
