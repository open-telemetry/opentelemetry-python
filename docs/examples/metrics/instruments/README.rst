OpenTelemetry Metrics SDK
=========================

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
            metrics:
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

The resulting metrics will appear in the output from the collector and look similar to this:

.. code-block:: sh

TODO
