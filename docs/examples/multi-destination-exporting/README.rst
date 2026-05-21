Multi-Destination Exporting
===========================

This example shows how to export telemetry data to multiple destinations
simultaneously. As described in the `OTLP specification
<https://opentelemetry.io/docs/specs/otlp/#multi-destination-exporting>`_,
each destination should have implemented its own queuing, acknowledgement
handling, and retry logic to prevent one slow or unavailable destination
from blocking the others.

The OpenTelemetry Python SDK achieves this by using a separate processor
or reader per destination:

* **Traces**: Use one ``BatchSpanProcessor`` per destination, each wrapping
  its own ``SpanExporter``. Add each processor to the ``TracerProvider``
  via ``add_span_processor()``.

* **Metrics**: Pass multiple ``MetricReader`` instances (each wrapping its
  own ``MetricExporter``) to the ``MeterProvider`` constructor via the
  ``metric_readers`` parameter.

* **Logs**: Use one ``BatchLogRecordProcessor`` per destination, each
  wrapping its own ``LogExporter``. Add each processor to the
  ``LoggerProvider`` via ``add_log_record_processor()``.

.. note::

   The **Profiles** signal is not yet supported in the Python SDK.
   When it becomes available, the same pattern will apply.

The source files of these examples are available :scm_web:`here <docs/examples/multi-destination-exporting/>`.

Installation
------------

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-exporter-otlp-proto-grpc
    pip install opentelemetry-exporter-otlp-proto-http
    pip install opentelemetry-instrumentation-logging # For LoggingHandler

Run the Example
---------------

.. code-block:: sh

    python multi_destination_traces.py
    python multi_destination_metrics.py
    python multi_destination_logs.py

The output will be shown in the console for the ``ConsoleSpanExporter``,
``ConsoleMetricExporter``, and ``ConsoleLogRecordExporter`` destinations.
The OTLP destinations require a running `collector
<https://opentelemetry.io/docs/collector/>`_.

Useful links
------------

- `OTLP multi-destination exporting specification <https://opentelemetry.io/docs/specs/otlp/#multi-destination-exporting>`_
- OpenTelemetry_
- :doc:`../../api/trace`
- :doc:`../../api/metrics`
- :doc:`../../api/_logs`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
