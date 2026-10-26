OpenTelemetry Python SDK Declarative Configuration
===================================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-configuration.svg
    :target: https://pypi.org/project/opentelemetry-configuration/

.. warning::

   This package is **experimental**. The API surface, type names, and behaviour
   may change between minor versions. Pin a specific version in production.

This package implements the `OpenTelemetry declarative configuration
specification <https://opentelemetry.io/docs/specs/otel/configuration/>`_ for
the Python SDK. It parses a YAML or JSON configuration file (or
programmatically-constructed configuration model) into typed dataclasses,
creates the SDK components it describes, and can install them as the global
SDK providers and propagator.

The standard activation path is the ``OTEL_CONFIG_FILE`` environment variable,
which the SDK's configurator picks up automatically. Set the variable and run
your app under ``opentelemetry-instrument``; no code change is required.

For programmatic use, configure the global SDK from a file:

.. code-block:: python

    from opentelemetry.configuration import configure_sdk, load_config

    components = configure_sdk(load_config("otel-config.yaml"))

``configure_sdk`` creates every component before setting any global, so a
configuration error leaves the global SDK untouched. To create components
without touching global state, use ``load_config`` and ``create_sdk``:

.. code-block:: python

    from opentelemetry.configuration import create_sdk, load_config

    components = create_sdk(load_config("otel-config.yaml"))
    tracer = components.tracer_provider.get_tracer(__name__)

Sections omitted from the configuration yield no-op providers (and a no-op
propagator). With ``disabled: true`` all providers are no-op, while the
configured propagator is still created.

Installation
------------

::

    pip install opentelemetry-configuration

References
----------

* `OpenTelemetry declarative configuration specification
  <https://opentelemetry.io/docs/specs/otel/configuration/>`_
* `Language support status matrix
  <https://github.com/open-telemetry/opentelemetry-configuration/blob/main/language-support-status.md#python>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
