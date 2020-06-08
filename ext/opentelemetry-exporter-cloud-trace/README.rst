OpenTelemetry Cloud Trace Exporters
===================================

This library provides classes for exporting trace data to Google Cloud Trace.

Installation
------------

::

    pip install opentelemetry-exporter-cloud-trace

Usage
-----

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        SimpleExportSpanProcessor,
    )

    trace.set_tracer_provider(TracerProvider())

    cloud_trace_exporter = CloudTraceSpanExporter(
        project_id='my-gcloud-project',
    )
    trace.get_tracer_provider().add_span_processor(
        SimpleExportSpanProcessor(cloud_trace_exporter)
    )
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span('foo'):
        print('Hello world!')



References
----------

* `Cloud Trace <https://cloud.google.com/trace/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
