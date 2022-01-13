OpenTelemetry Logs SDK
======================

.. warning::
   OpenTelemetry Python logs are in an experimental state. The APIs within
   :mod:`opentelemetry.sdk._logs` are subject to change in minor/patch releases and make no
   backward compatability guarantees at this time.

Start the Collector locally to see data being exported. Write the following file:

.. code-block:: yaml

    # otel-collector-config.yaml
    receivers:
    otlp:
        protocols:
        grpc:

    exporters:
    logging:

    processors:
    batch:

    service:
        pipelines:
            logs:
                receivers: [otlp]
                exporters: [logging]
  
Then start the Docker container:

.. code-block:: sh

    docker run \
        -p 4317:4317 \
        -v $(pwd)/otel-collector-config.yaml:/etc/otel/config.yaml \
        otel/opentelemetry-collector-contrib:latest

.. code-block:: sh

    $ python example.py

The resulting logs will appear in the output from the collector and look similar to this:

.. code-block:: sh

        Resource SchemaURL: 
        Resource labels:
            -> telemetry.sdk.language: STRING(python)
            -> telemetry.sdk.name: STRING(opentelemetry)
            -> telemetry.sdk.version: STRING(1.8.0)
            -> service.name: STRING(shoppingcart)
            -> service.instance.id: STRING(instance-12)
        InstrumentationLibraryLogs #0
        InstrumentationLibraryMetrics SchemaURL: 
        InstrumentationLibrary __main__ 0.1
        LogRecord #0
        Timestamp: 2022-01-13 20:37:03.998733056 +0000 UTC
        Severity: WARNING
        ShortName: 
        Body: Jail zesty vixen who grabbed pay from quack.
        Trace ID: 
        Span ID: 
        Flags: 0
        LogRecord #1
        Timestamp: 2022-01-13 20:37:04.082757888 +0000 UTC
        Severity: ERROR
        ShortName: 
        Body: The five boxing wizards jump quickly.
        Trace ID: 
        Span ID: 
        Flags: 0
        LogRecord #2
        Timestamp: 2022-01-13 20:37:04.082979072 +0000 UTC
        Severity: ERROR
        ShortName: 
        Body: Hyderabad, we have a major problem.
        Trace ID: 63491217958f126f727622e41d4460f3
        Span ID: d90c57d6e1ca4f6c
        Flags: 1