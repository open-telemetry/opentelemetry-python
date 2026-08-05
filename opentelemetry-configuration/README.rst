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
programmatically-constructed configuration model) into typed dataclasses and
applies the result to the global SDK providers.

The standard activation path is the ``OTEL_CONFIG_FILE`` environment variable,
which the SDK's configurator picks up automatically. Set the variable and run
your app under ``opentelemetry-instrument``; no code change is required.

For programmatic use:

.. code-block:: python

    from opentelemetry.configuration import configure_sdk, load_config_file

    config = load_config_file("otel-config.yaml")
    configure_sdk(config)

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
