OpenTelemetry Python API
========================

The OpenTelemetry Python API provides the core interfaces and no-op
implementations for instrumenting applications with traces, metrics, and logs.
It defines the abstract classes and data types that library authors and
application developers use to collect telemetry data. The API is designed to be
lightweight with minimal dependencies so that instrumentation libraries can
depend on it without pulling in the full SDK.

For the concrete implementation of these interfaces, see the
:doc:`OpenTelemetry Python SDK </sdk/index>`.

.. toctree::
    :maxdepth: 1

    _logs
    attributes
    baggage
    context
    propagate
    propagators
    trace
    metrics
    environment_variables
