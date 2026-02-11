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

"""Configuration file loading and parsing."""

import json
import logging
from pathlib import Path
from typing import Any

from opentelemetry.sdk._configuration.file._env_substitution import (
    substitute_env_vars,
)
from opentelemetry.sdk._configuration.models import OpenTelemetryConfiguration

try:
    import yaml
except ImportError as exc:
    raise ImportError(
        "File configuration requires pyyaml. "
        "Install with: pip install opentelemetry-sdk[file-configuration]"
    ) from exc

_logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration file loading, parsing, or validation fails.

    This includes errors from:
    - File not found or inaccessible
    - Invalid YAML/JSON syntax
    - Schema validation failures
    - Environment variable substitution errors
    """


def load_config_file(file_path: str) -> OpenTelemetryConfiguration:
    """Load and parse an OpenTelemetry configuration file.

    Supports YAML and JSON formats. Performs environment variable substitution
    before parsing.

    Args:
        file_path: Path to the configuration file (.yaml, .yml, or .json).

    Returns:
        Parsed OpenTelemetryConfiguration object.

    Raises:
        ConfigurationError: If file cannot be read, parsed, or validated.
        EnvSubstitutionError: If required environment variable is missing.

    Examples:
        >>> config = load_config_file("otel-config.yaml")
        >>> print(config.tracer_provider)
    """
    path = Path(file_path)

    if not path.exists():
        _logger.error("Configuration file not found: %s", file_path)
        raise ConfigurationError(f"Configuration file not found: {file_path}")

    if not path.is_file():
        _logger.error("Configuration path is not a file: %s", file_path)
        raise ConfigurationError(
            f"Configuration path is not a file: {file_path}"
        )

    try:
        with open(path, encoding="utf-8") as config_file:
            content = config_file.read()
    except (OSError, IOError) as exc:
        _logger.exception("Failed to read configuration file: %s", file_path)
        raise ConfigurationError(
            f"Failed to read configuration file: {file_path}"
        ) from exc

    # Perform environment variable substitution
    try:
        content = substitute_env_vars(content)
    except Exception as exc:
        raise ConfigurationError(
            f"Environment variable substitution failed: {exc}"
        ) from exc

    # Parse based on file extension
    suffix = path.suffix.lower()
    try:
        if suffix in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        elif suffix == ".json":
            data = json.loads(content)
        else:
            _logger.error("Unsupported file format: %s", suffix)
            raise ConfigurationError(
                f"Unsupported file format: {suffix}. Use .yaml, .yml, or .json"
            )
    except yaml.YAMLError as exc:
        _logger.exception("Failed to parse YAML from %s", file_path)
        raise ConfigurationError(f"Failed to parse YAML: {exc}") from exc
    except json.JSONDecodeError as exc:
        _logger.exception("Failed to parse JSON from %s", file_path)
        raise ConfigurationError(f"Failed to parse JSON: {exc}") from exc

    if data is None:
        _logger.error("Configuration file is empty: %s", file_path)
        raise ConfigurationError("Configuration file is empty")

    if not isinstance(data, dict):
        _logger.error(
            "Configuration must be a mapping/object, got %s",
            type(data).__name__,
        )
        raise ConfigurationError(
            f"Configuration must be a mapping/object, got {type(data).__name__}"
        )

    # Convert to OpenTelemetryConfiguration model
    try:
        config = _dict_to_model(data)
    except Exception as exc:
        _logger.exception(
            "Failed to validate configuration from %s", file_path
        )
        raise ConfigurationError(
            f"Failed to validate configuration: {exc}"
        ) from exc

    return config


def _dict_to_model(data: dict[str, Any]) -> OpenTelemetryConfiguration:
    """Convert dictionary to OpenTelemetryConfiguration model.

    Uses the generated dataclass from models.py. This provides basic
    validation through dataclass field types.

    Args:
        data: Parsed configuration dictionary.

    Returns:
        OpenTelemetryConfiguration instance.

    Raises:
        TypeError: If data doesn't match expected structure.
        ValueError: If values are invalid.
    """
    # The models.py file has dataclasses, so we need to recursively
    # construct them from dictionaries. For now, use a simple approach
    # that relies on dataclass construction.

    # This is a simplified implementation. A more robust version would
    # recursively handle nested dataclasses and discriminated unions.
    # For PR 1, we're focusing on basic loading - validation can be
    # enhanced in future PRs.

    try:
        # Attempt to construct the model
        # This will work for simple cases but may need enhancement
        # for complex nested structures
        config = OpenTelemetryConfiguration(**data)
        return config
    except TypeError as exc:
        # Provide more helpful error message
        raise TypeError(
            f"Configuration structure is invalid. "
            f"Check that all required fields are present and correctly typed: {exc}"
        ) from exc
