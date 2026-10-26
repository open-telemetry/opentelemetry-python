# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OpenTelemetry SDK File Configuration.

This module provides support for parsing declarative configuration files
(YAML or JSON) and creating SDK components from them.

Example:
    >>> from opentelemetry.configuration.file import load_config
    >>> config = load_config("otel-config.yaml")
    >>> print(config.file_format)
    '1.0'
"""

from opentelemetry.configuration._exceptions import (
    ConfigurationError,
    MissingDependencyError,
)
from opentelemetry.configuration._logger_provider import (
    create_logger_provider,
)
from opentelemetry.configuration._meter_provider import (
    create_meter_provider,
)
from opentelemetry.configuration._propagator import create_propagator
from opentelemetry.configuration._resource import create_resource
from opentelemetry.configuration._tracer_provider import (
    create_tracer_provider,
)
from opentelemetry.configuration.file._env_substitution import (
    substitute_env_vars,
)
from opentelemetry.configuration.file._loader import (
    ConfigFileFormat,
    load_config,
)

__all__ = [
    "ConfigFileFormat",
    "ConfigurationError",
    "MissingDependencyError",
    "create_logger_provider",
    "create_meter_provider",
    "create_propagator",
    "create_resource",
    "create_tracer_provider",
    "load_config",
    "substitute_env_vars",
]
