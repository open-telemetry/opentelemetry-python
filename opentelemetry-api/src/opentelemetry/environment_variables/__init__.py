# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Names of the ``OTEL_*`` environment variables the API package defines.

Each name in this module is bound to a constant so that code refers to the
environment variable by symbol rather than by a repeated string literal.
Defining a name here does not mean the API reads it: ``OTEL_LOGS_EXPORTER``,
``OTEL_METRICS_EXPORTER``, ``OTEL_TRACES_EXPORTER`` and
``OTEL_PYTHON_ID_GENERATOR`` are defined here and read only by
``opentelemetry.sdk._configuration``. The environment variables the SDK both
defines and reads live in :mod:`opentelemetry.sdk.environment_variables`.
"""

OTEL_LOGS_EXPORTER = "OTEL_LOGS_EXPORTER"
"""
.. envvar:: OTEL_LOGS_EXPORTER

Specifies which exporter is used for logs. See `General SDK Configuration
<https://opentelemetry.io/docs/concepts/sdk-configuration/general-sdk-configuration/#otel_logs_exporter>`__.

**Default value:** ``"otlp"``

**Example:**

``export OTEL_LOGS_EXPORTER="console"``

Accepted values for ``OTEL_LOGS_EXPORTER`` are:

- ``"otlp"``
- ``"console"``
- ``"none"``: No automatically configured exporter for logs.

.. note::

    Exporter packages may add entry points for group ``opentelemetry_logs_exporter`` which
    can then be used with this environment variable by name. The entry point should point to
    a `opentelemetry.sdk._logs.export.LogRecordExporter` subclass; it must be constructable
    without any required arguments. This mechanism is considered experimental and may change
    in the future.
"""

OTEL_METRICS_EXPORTER = "OTEL_METRICS_EXPORTER"
"""
.. envvar:: OTEL_METRICS_EXPORTER

Specifies which exporter is used for metrics. See `General SDK Configuration
<https://opentelemetry.io/docs/concepts/sdk-configuration/general-sdk-configuration/#otel_metrics_exporter>`_.

**Default value:** ``"otlp"``

**Example:**

``export OTEL_METRICS_EXPORTER="prometheus"``

Accepted values for ``OTEL_METRICS_EXPORTER`` are:

- ``"otlp"``
- ``"prometheus"``
- ``"none"``: No automatically configured exporter for metrics.

.. note::

    Exporter packages may add entry points for group ``opentelemetry_metrics_exporter`` which
    can then be used with this environment variable by name. The entry point should point to
    either a `opentelemetry.sdk.metrics.export.MetricExporter` (push exporter) or
    `opentelemetry.sdk.metrics.export.MetricReader` (pull exporter) subclass; it must be
    constructable without any required arguments. This mechanism is considered experimental and
    may change in subsequent releases.
"""

OTEL_PROPAGATORS = "OTEL_PROPAGATORS"
"""
.. envvar:: OTEL_PROPAGATORS
"""

OTEL_PYTHON_CONTEXT = "OTEL_PYTHON_CONTEXT"
"""
.. envvar:: OTEL_PYTHON_CONTEXT
"""

OTEL_PYTHON_ID_GENERATOR = "OTEL_PYTHON_ID_GENERATOR"
"""
.. envvar:: OTEL_PYTHON_ID_GENERATOR
"""

OTEL_TRACES_EXPORTER = "OTEL_TRACES_EXPORTER"
"""
.. envvar:: OTEL_TRACES_EXPORTER
"""

OTEL_PYTHON_TRACER_PROVIDER = "OTEL_PYTHON_TRACER_PROVIDER"
"""
.. envvar:: OTEL_PYTHON_TRACER_PROVIDER
"""

OTEL_PYTHON_METER_PROVIDER = "OTEL_PYTHON_METER_PROVIDER"
"""
.. envvar:: OTEL_PYTHON_METER_PROVIDER
"""

_OTEL_PYTHON_LOGGER_PROVIDER = "OTEL_PYTHON_LOGGER_PROVIDER"
"""
.. envvar:: OTEL_PYTHON_LOGGER_PROVIDER
"""
