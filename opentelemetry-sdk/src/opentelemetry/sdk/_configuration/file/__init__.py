# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OpenTelemetry SDK File Configuration.

This module provides support for configuring the OpenTelemetry SDK
using declarative configuration files (YAML or JSON).

Example:
    >>> from opentelemetry.sdk._configuration.file import load_config_file
    >>> config = load_config_file("otel-config.yaml")
    >>> print(config.file_format)
    '1.0'
"""

from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration._meter_provider import (
    configure_meter_provider,
    create_meter_provider,
)
from opentelemetry.sdk._configuration._propagator import (
    configure_propagator,
    create_propagator,
)
from opentelemetry.sdk._configuration._resource import create_resource
from opentelemetry.sdk._configuration.file._env_substitution import (
    EnvSubstitutionError,
    substitute_env_vars,
)
from opentelemetry.sdk._configuration.file._loader import load_config_file

__all__ = [
    "load_config_file",
    "substitute_env_vars",
    "ConfigurationError",
    "EnvSubstitutionError",
    "create_resource",
    "create_propagator",
    "configure_propagator",
    "create_meter_provider",
    "configure_meter_provider",
]
