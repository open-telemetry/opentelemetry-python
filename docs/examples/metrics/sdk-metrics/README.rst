SDK Metrics
===========

Some SDK components can emit telemetry about their internal state according to the `semantic conventions for OpenTelemetry SDK metrics <https://opentelemetry.io/docs/specs/semconv/otel/sdk-metrics/>`. At the time of writing these semantic conventions are still in development and in order to have them exported you need to set the ``OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED`` environment variable to ``true``.

The provided :scm_web:`sdk_metrics.py <docs/examples/metrics/sdk-metrics/sdk_metrics.py>` example shows how to setup manually the SDK in order to send them.

Installation
------------

.. code-block:: sh

    pip install -r requirements.txt

Run the Example
---------------

Start an OTLP HTTP collector or compatible backend listening on the default
endpoint, ``http://localhost:4318``. To use a different endpoint, configure
``OTEL_EXPORTER_OTLP_ENDPOINT`` or the signal-specific OTLP exporter
environment variables.

.. code-block:: sh

    python sdk_metrics.py

The example sends a span, a log record, and the OpenTelemetry SDK health
metrics emitted by the configured SDK components.

Useful links
------------

- OpenTelemetry_
- :doc:`../../../api/metrics`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
