OpenTelemetry Stackdriver Exporters
=====================================

This library provides integration with Google Cloud Stackdriver.

Installation
------------

::

    pip install opentelemetry-ext-stackdriver

Usage
-----

.. code:: python

    from opentelemetry import trace
    from opentelemetry.ext import stackdriver
    from opentelemetry.sdk.trace import Tracer
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

    trace.set_preferred_tracer_implementation(lambda T: Tracer())
    tracer = trace.tracer()

    # create a StackdriverSpanExporter
    stackdriver_exporter = stackdriver.StackdriverSpanExporter(
        project_id='my-helloworld-project',
    )

    # Create a BatchExportSpanProcessor and add the exporter to it
    span_processor = BatchExportSpanProcessor(stackdriver_exporter)

    # add to the tracer
    tracer.add_span_processor(span_processor)

    with tracer.start_as_current_span('foo'):
        print('Hello world!')

References
----------

* `Stackdriver <https://cloud.google.com/stackdriver/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
