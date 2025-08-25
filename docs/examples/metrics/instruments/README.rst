OpenTelemetry Metrics SDK
=========================

The source files of these examples are available :scm_web:`here <docs/examples/metrics/instruments/>`.

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

    processors:
        batch:

    service:
        pipelines:
            metrics:
                receivers: [otlp]
                exporters: [debug]
  
Then start the Docker container:

.. code-block:: sh

    docker run \
        -p 4317:4317 \
        -v $(pwd)/otel-collector-config.yaml:/etc/otel/config.yaml \
        otel/opentelemetry-collector-contrib:latest

.. code-block:: sh

    $ python example.py

The resulting metrics will appear in the output from the collector and look similar to this:

.. code-block:: sh

    ScopeMetrics #0
    ScopeMetrics SchemaURL:
    InstrumentationScope getting-started 0.1.2
    Metric #0
    Descriptor:
         -> Name: counter
         -> Description:
         -> Unit:
         -> DataType: Sum
         -> IsMonotonic: true
         -> AggregationTemporality: Cumulative
    NumberDataPoints #0
    StartTimestamp: 2024-08-09 11:21:42.145179 +0000 UTC
    Timestamp: 2024-08-09 11:21:42.145325 +0000 UTC
    Value: 1
    Metric #1
    Descriptor:
         -> Name: updown_counter
         -> Description:
         -> Unit:
         -> DataType: Sum
         -> IsMonotonic: false
         -> AggregationTemporality: Cumulative
    NumberDataPoints #0
    StartTimestamp: 2024-08-09 11:21:42.145202 +0000 UTC
    Timestamp: 2024-08-09 11:21:42.145325 +0000 UTC
    Value: -4
    Metric #2
    Descriptor:
         -> Name: histogram
         -> Description:
         -> Unit:
         -> DataType: Histogram
         -> AggregationTemporality: Cumulative
    HistogramDataPoints #0
    StartTimestamp: 2024-08-09 11:21:42.145221 +0000 UTC
    Timestamp: 2024-08-09 11:21:42.145325 +0000 UTC
    Count: 1
