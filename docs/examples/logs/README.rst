OpenTelemetry Logs SDK
======================

.. warning::
   OpenTelemetry Python logs are in an experimental state. The APIs within
   :mod:`opentelemetry.sdk._logs` are subject to change in minor/patch releases and make no
   backward compatibility guarantees at this time.

Start the Collector locally to see data being exported. Write the following file:

.. code-block:: yaml

    # otel-collector-config.yaml
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317

    exporters:
      debug:
        verbosity: detailed

    processors:
      batch:

    service:
        pipelines:
            logs:
                receivers: [otlp]
                processors: [batch]
                exporters: [debug]
            traces:
                receivers: [otlp]
                processors: [batch]
                exporters: [debug]

Then start the Docker container:

.. code-block:: sh

    docker run \
        -p 4317:4317 \
        -v $(pwd)/otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml \
        otel/opentelemetry-collector-contrib:latest

.. code-block:: sh

    $ python example.py

The resulting logs will appear in the output from the collector and look similar to this:

.. code-block:: sh

    ResourceLog #0
    Resource SchemaURL: 
    Resource attributes:
        -> telemetry.sdk.language: Str(python)
        -> telemetry.sdk.name: Str(opentelemetry)
        -> telemetry.sdk.version: Str(1.33.0.dev0)
        -> service.name: Str(shoppingcart)
        -> service.instance.id: Str(instance-12)
    ScopeLogs #0
    ScopeLogs SchemaURL: 
    InstrumentationScope myapp.area2 
    LogRecord #0
    ObservedTimestamp: 2025-04-22 12:16:57.315179 +0000 UTC
    Timestamp: 2025-04-22 12:16:57.315152896 +0000 UTC
    SeverityText: WARN
    SeverityNumber: Warn(13)
    Body: Str(Jail zesty vixen who grabbed pay from quack.)
    Attributes:
        -> code.filepath: Str(/Users/jayclifford/Repos/opentelemetry-python/docs/examples/logs/example.py)
        -> code.function: Str(<module>)
        -> code.lineno: Int(47)
    Trace ID: 
    Span ID: 
    Flags: 0
    LogRecord #1
    ObservedTimestamp: 2025-04-22 12:16:57.31522 +0000 UTC
    Timestamp: 2025-04-22 12:16:57.315213056 +0000 UTC
    SeverityText: ERROR
    SeverityNumber: Error(17)
    Body: Str(The five boxing wizards jump quickly.)
    Attributes:
        -> code.filepath: Str(/Users/jayclifford/Repos/opentelemetry-python/docs/examples/logs/example.py)
        -> code.function: Str(<module>)
        -> code.lineno: Int(48)
    Trace ID: 
    Span ID: 
    Flags: 0
    LogRecord #2
    ObservedTimestamp: 2025-04-22 12:16:57.315445 +0000 UTC
    Timestamp: 2025-04-22 12:16:57.31543808 +0000 UTC
    SeverityText: ERROR
    SeverityNumber: Error(17)
    Body: Str(Hyderabad, we have a major problem.)
    Attributes:
        -> code.filepath: Str(/Users/jayclifford/Repos/opentelemetry-python/docs/examples/logs/example.py)
        -> code.function: Str(<module>)
        -> code.lineno: Int(61)
    Trace ID: 8a6739fffce895e694700944e2faf23e
    Span ID: a45337020100cb63
    Flags: 1
    ScopeLogs #1
    ScopeLogs SchemaURL: 
    InstrumentationScope myapp.area1 
    LogRecord #0
    ObservedTimestamp: 2025-04-22 12:16:57.315242 +0000 UTC
    Timestamp: 2025-04-22 12:16:57.315234048 +0000 UTC
    SeverityText: ERROR
    SeverityNumber: Error(17)
    Body: Str(I have custom attributes.)
    Attributes:
        -> user_id: Str(user-123)
        -> code.filepath: Str(/Users/jayclifford/Repos/opentelemetry-python/docs/examples/logs/example.py)
        -> code.function: Str(<module>)
        -> code.lineno: Int(53)
    Trace ID: 
    Span ID: 
    Flags: 0
