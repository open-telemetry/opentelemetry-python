# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OpenTelemetry SDK Declarative Configuration.

This package implements the OpenTelemetry declarative configuration
specification for the Python SDK: parse a YAML or JSON configuration file
into a configuration model, create SDK components from a model or do both
and install the result as the process-global SDK.

The standard activation path is the ``OTEL_CONFIG_FILE`` environment
variable, which the SDK's configurator picks up automatically. For
programmatic use, configure the global SDK from a file:

>>> from opentelemetry.configuration import configure_sdk, load_config
>>> components = configure_sdk(load_config("otel-config.yaml"))

Or parse and create components without touching any global state:

>>> from opentelemetry.configuration import create_sdk, load_config
>>> components = create_sdk(load_config("otel-config.yaml"))
>>> tracer = components.tracer_provider.get_tracer(__name__)

A configuration model can also be built in code:

>>> from opentelemetry.configuration import (
...     OpenTelemetryConfiguration,
...     create_sdk,
... )
>>> components = create_sdk(OpenTelemetryConfiguration(file_format="1.0"))

This package is **experimental**. The API surface, type names, and
behavior may change between minor versions.
"""

from opentelemetry.configuration._exceptions import ConfigurationError
from opentelemetry.configuration._sdk import (
    SdkComponents,
    configure_sdk,
    create_sdk,
)
from opentelemetry.configuration.file._loader import load_config
from opentelemetry.configuration.models import OpenTelemetryConfiguration

__all__ = [
    "ConfigurationError",
    "OpenTelemetryConfiguration",
    "SdkComponents",
    "configure_sdk",
    "create_sdk",
    "load_config",
]
