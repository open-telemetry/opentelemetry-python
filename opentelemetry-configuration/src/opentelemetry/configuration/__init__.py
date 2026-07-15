# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OpenTelemetry SDK Declarative Configuration.

This package implements the OpenTelemetry declarative configuration
specification for the Python SDK. Load a YAML or JSON configuration file
(or build a configuration model programmatically) and apply it to the
process-global SDK providers.

The standard activation path is the ``OTEL_CONFIG_FILE`` environment
variable, which the SDK's configurator picks up automatically. For
programmatic use:

>>> from opentelemetry.configuration import (
...     load_config_file, configure_sdk,
... )
>>> config = load_config_file("otel-config.yaml")
>>> configure_sdk(config)

Construct a configuration programmatically and apply it:

>>> from opentelemetry.configuration import (
...     OpenTelemetryConfiguration, configure_sdk,
... )
>>> configure_sdk(OpenTelemetryConfiguration(file_format="1.0-rc.1"))

This package is **experimental**. The API surface, type names, and
behaviour may change between minor versions.
"""

from opentelemetry.configuration._exceptions import ConfigurationError
from opentelemetry.configuration._sdk import configure_sdk
from opentelemetry.configuration.file._loader import load_config_file
from opentelemetry.configuration.models import OpenTelemetryConfiguration

__all__ = [
    "ConfigurationError",
    "OpenTelemetryConfiguration",
    "configure_sdk",
    "load_config_file",
]
