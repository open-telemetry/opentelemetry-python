Declarative Configuration
=========================

.. note::

   Declarative configuration support is new in this release and may still
   have rough edges. If you hit a problem, please open an issue on the
   `opentelemetry-python tracker
   <https://github.com/open-telemetry/opentelemetry-python/issues>`_.

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

Declarative configuration lives in a separate, experimental package:

.. code-block:: sh

    pip install opentelemetry-configuration

Enabling with an environment variable
-------------------------------------

Point the SDK at a file with the ``OTEL_CONFIG_FILE`` environment variable.
When it is set, the file is the sole source of SDK construction. Spec-defined
``OTEL_*`` variables with schema equivalents are ignored. Environment variables
can still be read via ``${env:VAR}`` substitution inside the file (see
`Environment variable substitution`_).

.. code-block:: sh

    export OTEL_CONFIG_FILE=/etc/otel/otel-config.yaml
    opentelemetry-instrument python app.py

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
                endpoint: https://example.com:4318/v1/traces
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
                endpoint: https://example.com:4318/v1/metrics
                headers:
                  - name: api-key
                    value: ${OTLP_API_KEY}

    logger_provider:
      processors:
        - batch:
            exporter:
              otlp_http:
                endpoint: https://example.com:4318/v1/logs
                headers:
                  - name: api-key
                    value: ${OTLP_API_KEY}

Environment variable substitution
----------------------------------

Values in the file may reference environment variables, which keeps secrets
such as API keys out of the file itself. Substitution happens before the file
is parsed.

* ``${VAR}``: replaced with the value of ``VAR``. If ``VAR`` is unset, loading
  fails with an error.
* ``${VAR:-default}``: replaced with ``VAR`` if set, otherwise ``default``.
* ``$$``: a literal ``$``.

In the example above, ``${OTLP_API_KEY}`` is required, while
``${DEPLOYMENT_ENVIRONMENT:-development}`` falls back to ``development`` when
unset.

Behavior notes
--------------

* When ``OTEL_CONFIG_FILE`` is set, the file is authoritative for SDK
  construction; spec-defined ``OTEL_*`` variables with schema equivalents are
  not consulted. Environment variables can still be read indirectly by
  components the file enables (for example resource detectors) and via
  ``${env:VAR}`` substitution.
* Python-implementation extensions (``OTEL_PYTHON_*`` variables such as
  ``OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED`` or
  ``OTEL_PYTHON_TRACER_CONFIGURATOR``) are **not** applied when
  ``OTEL_CONFIG_FILE`` is set: the env-var initialisation path is skipped
  entirely. If your app currently relies on one of these and you are
  migrating to a config file, plan to capture the equivalent behaviour in
  the file (or in code) instead.
* Sections omitted from the file leave the corresponding global provider
  unset (a no-op provider), per the specification.
* Setting ``disabled: true`` at the top level turns the SDK into a no-op.

See also
--------

* `OpenTelemetry configuration specification
  <https://opentelemetry.io/docs/specs/otel/configuration/>`_
* :doc:`environment_variables`: the environment-variable configuration path
