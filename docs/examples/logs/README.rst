OpenTelemetry Logs SDK
======================

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

        ResourceLog #0
        Resource labels:
             -> telemetry.sdk.language: STRING(python)
             -> telemetry.sdk.name: STRING(opentelemetry)
             -> telemetry.sdk.version: STRING(1.5.0.dev0)
             -> service.name: STRING(unknown_service)
        InstrumentationLibraryLogs #0
        InstrumentationLibrary __main__ 0.1
        LogRecord #0
        Timestamp: 2021-08-18 08:26:53.837349888 +0000 UTC
        Severity: ERROR
        ShortName:
        Body: Exception while exporting logs.
        ResourceLog #1
        Resource labels:
             -> telemetry.sdk.language: STRING(python)
             -> telemetry.sdk.name: STRING(opentelemetry)
             -> telemetry.sdk.version: STRING(1.5.0.dev0)
             -> service.name: STRING(unknown_service)
        InstrumentationLibraryLogs #0
        InstrumentationLibrary __main__ 0.1
        LogRecord #0
        Timestamp: 2021-08-18 08:26:53.842546944 +0000 UTC
        Severity: ERROR
        ShortName:
        Body: The five boxing wizards jump quickly.
        ResourceLog #2
        Resource labels:
             -> telemetry.sdk.language: STRING(python)
             -> telemetry.sdk.name: STRING(opentelemetry)
             -> telemetry.sdk.version: STRING(1.5.0.dev0)
             -> service.name: STRING(unknown_service)
        InstrumentationLibraryLogs #0
        InstrumentationLibrary __main__ 0.1
        LogRecord #0
        Timestamp: 2021-08-18 08:26:53.843979008 +0000 UTC
        Severity: ERROR
        ShortName:
        Body: Hyderabad, we have a major problem.