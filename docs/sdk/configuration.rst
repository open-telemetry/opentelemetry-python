Declarative Configuration
=========================

Declarative configuration lets you configure the OpenTelemetry SDK from a
single YAML (or JSON) file instead of setting many individual ``OTEL_*``
environment variables or writing provider-construction code by hand. The file
format is defined by the `OpenTelemetry configuration specification
<https://opentelemetry.io/docs/specs/otel/configuration/>`_.

A single file describes your resource, providers, processors, exporters,
samplers, and propagators. The SDK reads the file, validates it against the
configuration schema, and applies it globally.

Installing
----------

File configuration relies on optional dependencies (``pyyaml`` and
``jsonschema``). Install them with the ``file-configuration`` extra:

.. code-block:: sh

    pip install "opentelemetry-sdk[file-configuration]"

Enabling with an environment variable
-------------------------------------

The simplest way to use declarative configuration is to point the SDK at a
file with the ``OTEL_CONFIG_FILE`` environment variable. When it is set, the
file is the sole source of configuration and other ``OTEL_*`` variables are
ignored (except where referenced inside the file — see
`Environment variable substitution`_).

.. code-block:: sh

    export OTEL_CONFIG_FILE=/etc/otel/otel-config.yaml
    opentelemetry-instrument python app.py

Configuring programmatically
----------------------------

You can also load and apply a configuration file directly. This is useful when
you want to construct or inspect the configuration in code:

.. code-block:: python

    from opentelemetry.sdk.configuration import configure_sdk, load_config_file

    config = load_config_file("otel-config.yaml")
    configure_sdk(config)

``load_config_file`` parses and validates the file and returns a typed
``OpenTelemetryConfiguration`` object; ``configure_sdk`` applies it to the
global tracer, meter, and logger providers and the global propagator. A failure
to read, parse, or validate the file raises ``ConfigurationError``.

Example configuration
---------------------

The following file configures traces, metrics, and logs to be exported over
OTLP/HTTP. The source is available :scm_web:`here
<docs/examples/declarative-config/>`.

.. code-block:: yaml

    file_format: "1.0"

    resource:
      attributes:
        - name: service.name
          value: my-service
        - name: deployment.environment.name
          value: ${DEPLOYMENT_ENVIRONMENT:-development}

    tracer_provider:
      processors:
        - batch:
            exporter:
              otlp_http:
                endpoint: https://otlp.example.com:4318/v1/traces
                headers:
                  - name: api-key
                    value: ${OTLP_API_KEY}
      sampler:
        parent_based:
          root:
            always_on: {}

    meter_provider:
      readers:
        - periodic:
            interval: 60000
            exporter:
              otlp_http:
                endpoint: https://otlp.example.com:4318/v1/metrics
                headers:
                  - name: api-key
                    value: ${OTLP_API_KEY}

    logger_provider:
      processors:
        - batch:
            exporter:
              otlp_http:
                endpoint: https://otlp.example.com:4318/v1/logs
                headers:
                  - name: api-key
                    value: ${OTLP_API_KEY}

Environment variable substitution
----------------------------------

Values in the file may reference environment variables, which keeps secrets
such as API keys out of the file itself. Substitution happens before the file
is parsed.

* ``${VAR}`` — replaced with the value of ``VAR``. If ``VAR`` is unset, loading
  fails with an error.
* ``${VAR:-default}`` — replaced with ``VAR`` if set, otherwise ``default``.
* ``$$`` — a literal ``$``.

In the example above, ``${OTLP_API_KEY}`` is required, while
``${DEPLOYMENT_ENVIRONMENT:-development}`` falls back to ``development`` when
unset.

Behavior notes
--------------

* When ``OTEL_CONFIG_FILE`` is set, the file is authoritative; other ``OTEL_*``
  environment variables are not consulted.
* Sections omitted from the file leave the corresponding global provider
  unset (a no-op provider), per the specification.
* Setting ``disabled: true`` at the top level turns the SDK into a no-op.

See also
--------

* `OpenTelemetry configuration specification
  <https://opentelemetry.io/docs/specs/otel/configuration/>`_
* :doc:`environment_variables` — the environment-variable configuration path
