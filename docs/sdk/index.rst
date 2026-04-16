OpenTelemetry Python SDK
========================

The OpenTelemetry Python SDK provides the reference implementation of the
:doc:`OpenTelemetry Python API </api/index>`. It includes the concrete classes
for managing and exporting traces, metrics, and logs — such as
``TracerProvider``, ``MeterProvider``, span processors, metric readers, and
exporters. The SDK is responsible for sampling, batching, and delivering
telemetry data to backends.

Install the SDK in your application to configure how telemetry is collected,
processed, and exported.

.. toctree::
    :maxdepth: 1

    _logs
    resources
    trace
    metrics
    error_handler
    environment_variables
