Declarative Configuration
=========================

This example configures the OpenTelemetry SDK from a single YAML file using
:doc:`declarative configuration </sdk/configuration>` instead of environment
variables or hand-written provider setup.

The source files of this example are available :scm_web:`here
<docs/examples/declarative-config/>`.

Install the SDK with the ``file-configuration`` extra (it pulls in ``pyyaml``
and ``jsonschema``) along with the OTLP/HTTP exporter:

.. code-block:: sh

    pip install "opentelemetry-sdk[file-configuration]" \
        opentelemetry-exporter-otlp-proto-http

Start an OTLP-capable backend locally so there is somewhere to send data. Write
the following file:

.. code-block:: yaml

    # otel-collector-config.yaml
    receivers:
      otlp:
        protocols:
          http:
            endpoint: 0.0.0.0:4318

    exporters:
      debug:
        verbosity: detailed

    service:
        pipelines:
            traces:
                receivers: [otlp]
                exporters: [debug]
            metrics:
                receivers: [otlp]
                exporters: [debug]
            logs:
                receivers: [otlp]
                exporters: [debug]

Then start the Collector:

.. code-block:: sh

    docker run \
        -p 4318:4318 \
        -v $(pwd)/otel-collector-config.yaml:/etc/otel-collector-config.yaml \
        otel/opentelemetry-collector:latest \
        --config=/etc/otel-collector-config.yaml

Apply the configuration programmatically
----------------------------------------

``app.py`` loads ``otel-config.yaml`` and applies it with ``configure_sdk``:

.. code-block:: python

    from opentelemetry.sdk.configuration import configure_sdk, load_config_file

    configure_sdk(load_config_file("otel-config.yaml"))

Run it:

.. code-block:: sh

    python app.py

You should see the exported span in the Collector's debug output.

Apply the configuration with an environment variable
----------------------------------------------------

Alternatively, point the SDK at the file with ``OTEL_CONFIG_FILE`` and let
auto-instrumentation apply it — no configuration code in your application:

.. code-block:: sh

    export OTEL_CONFIG_FILE=$(pwd)/otel-config.yaml
    opentelemetry-instrument python app.py

Environment variable substitution
----------------------------------

``otel-config.yaml`` uses ``${DEPLOYMENT_ENVIRONMENT:-development}`` to read the
deployment environment from the environment, defaulting to ``development``. Set
it before running to override:

.. code-block:: sh

    export DEPLOYMENT_ENVIRONMENT=staging
