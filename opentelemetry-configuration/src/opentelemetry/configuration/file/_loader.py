# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Configuration file loading and parsing."""

import importlib.resources
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from opentelemetry.configuration._conversion import _dict_to_dataclass
from opentelemetry.configuration._exceptions import (
    ConfigurationError,
    MissingDependencyError,
)
from opentelemetry.configuration.file._env_substitution import (
    EnvSubstitutionError,
    substitute_env_vars,
)
from opentelemetry.configuration.models import OpenTelemetryConfiguration

try:
    import yaml
except ImportError as exc:
    raise MissingDependencyError(
        package="pyyaml",
        feature="File configuration",
        install_name="opentelemetry-sdk",
        extras="file-configuration",
    ) from exc

try:
    import jsonschema
except ImportError as exc:
    raise MissingDependencyError(
        package="jsonschema",
        feature="File configuration",
        install_name="opentelemetry-sdk",
        extras="file-configuration",
    ) from exc

# Schema version vendored in schema.json. ``file_format`` values are accepted
# per the configuration spec's versioning rules: the major version must match,
# and a minor version newer than the one this SDK targets is accepted with a
# warning. See
# https://github.com/open-telemetry/opentelemetry-configuration/blob/main/VERSIONING.md
_SUPPORTED_SCHEMA_MAJOR = 1
_SUPPORTED_SCHEMA_MINOR = 0

_schema_cache: list[dict] = []


def _get_schema() -> dict:
    if not _schema_cache:
        schema_path = (
            importlib.resources.files("opentelemetry.configuration")
            / "schema.json"
        )
        _schema_cache.append(
            json.loads(schema_path.read_text(encoding="utf-8"))
        )
    return _schema_cache[0]


_logger = logging.getLogger(__name__)

_YAML_STR_TAG = "tag:yaml.org,2002:str"

# A scalar whose entire value is a single ``${VAR}`` / ``${VAR:-default}``
# reference. Only such standalone references (when unquoted) have their type
# re-interpreted after substitution; embedded or multiple references resolve to
# a string per the configuration spec. A leading ``$$`` escape does not match,
# so ``$${VAR}`` is treated as an embedded (string) value.
_STANDALONE_ENV_REF = re.compile(
    r"\A\$\{[A-Za-z_][A-Za-z0-9_]*(?::-[^}]*)?\}\Z"
)


def _substitute_env_in_yaml_node(node: yaml.Node, loader: yaml.SafeLoader):
    """Apply env-var substitution to string scalar values in a YAML node tree.

    Substitution runs after parsing on scalar *values* only, so comments and
    mapping keys are never candidates (per the configuration spec). For an
    unquoted standalone ``${VAR}`` reference the node's type tag is re-resolved
    from the substituted value so YAML type coercion still applies (e.g.
    ``${LIMIT}`` -> int); quoted or embedded references stay strings.
    """
    if isinstance(node, yaml.ScalarNode):
        if node.tag == _YAML_STR_TAG:
            raw = node.value
            node.value = substitute_env_vars(raw)
            if node.style is None and _STANDALONE_ENV_REF.match(raw):
                node.tag = loader.resolve(
                    yaml.ScalarNode, node.value, (True, False)
                )
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            _substitute_env_in_yaml_node(item, loader)
    elif isinstance(node, yaml.MappingNode):
        # Recurse into values only; keys are not substitution candidates.
        for _key_node, value_node in node.value:
            _substitute_env_in_yaml_node(value_node, loader)


def _substitute_env_in_json_value(value: Any) -> Any:
    """Recursively apply env-var substitution to string values in JSON data.

    JSON has explicit types and no comments, so substitution applies only to
    string values (the result stays a string) and mapping keys are left as-is.
    """
    if isinstance(value, str):
        return substitute_env_vars(value)
    if isinstance(value, list):
        return [_substitute_env_in_json_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _substitute_env_in_json_value(val)
            for key, val in value.items()
        }
    return value


def _parse_config_content(
    content: str, suffix: str, file_path: str | os.PathLike[str]
) -> Any:
    """Parse configuration text and substitute environment variables.

    Parsing happens first, so ``${VAR}`` references in comments and mapping
    keys are never substitution candidates; substitution then runs on scalar
    values, with YAML node types re-resolved for standalone references.

    Raises:
        ConfigurationError: If the content cannot be parsed or substitution of
            a required environment variable fails.
    """
    try:
        if suffix == ".json":
            return _substitute_env_in_json_value(json.loads(content))
        yaml_loader = yaml.SafeLoader(content)
        try:
            root_node = yaml_loader.get_single_node()
            if root_node is None:
                return None
            _substitute_env_in_yaml_node(root_node, yaml_loader)
            return yaml_loader.construct_document(root_node)
        finally:
            yaml_loader.dispose()
    except EnvSubstitutionError as exc:
        raise ConfigurationError(
            f"Environment variable substitution failed: {exc}"
        ) from exc
    except yaml.YAMLError as exc:
        _logger.exception("Failed to parse YAML from %s", file_path)
        raise ConfigurationError(f"Failed to parse YAML: {exc}") from exc
    except json.JSONDecodeError as exc:
        _logger.exception("Failed to parse JSON from %s", file_path)
        raise ConfigurationError(f"Failed to parse JSON: {exc}") from exc


def load_config_file(
    file_path: str | os.PathLike[str],
) -> OpenTelemetryConfiguration:
    """Load and parse an OpenTelemetry configuration file.

    Supports YAML and JSON formats. Environment variable substitution is
    performed after parsing, on scalar values only, so ``${VAR}`` references in
    comments or mapping keys are left untouched.

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
    except OSError as exc:
        _logger.exception("Failed to read configuration file: %s", file_path)
        raise ConfigurationError(
            f"Failed to read configuration file: {file_path}"
        ) from exc

    # Parse the file, then substitute environment variables in scalar values.
    # Parsing first means comments and mapping keys are never substitution
    # candidates, and node types are still resolved after substitution.
    suffix = path.suffix.lower()
    if suffix not in (".yaml", ".yml", ".json"):
        _logger.error("Unsupported file format: %s", suffix)
        raise ConfigurationError(
            f"Unsupported file format: {suffix}. Use .yaml, .yml, or .json"
        )

    data = _parse_config_content(content, suffix, file_path)

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

    _validate_schema(data)
    _validate_file_format(data)

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


def _validate_schema(data: dict) -> None:
    """Validate configuration dict against the OTel configuration JSON schema.

    Raises:
        ConfigurationError: If the data does not conform to the schema.
    """
    try:
        jsonschema.validate(
            instance=data,
            schema=_get_schema(),
            cls=jsonschema.Draft202012Validator,
        )
    except jsonschema.ValidationError as exc:
        raise ConfigurationError(
            f"Configuration does not match schema: {exc.message} "
            f"(at {' -> '.join(str(p) for p in exc.absolute_path)})"
            if exc.absolute_path
            else f"Configuration does not match schema: {exc.message}"
        ) from exc
    except jsonschema.SchemaError as exc:
        raise ConfigurationError(
            f"Invalid configuration schema: {exc.message}"
        ) from exc


def _validate_file_format(data: dict) -> None:
    """Validate the ``file_format`` version per the configuration spec.

    The spec requires implementations to fail on an unsupported major version
    (a breaking-change boundary) and to accept, with a warning, a minor version
    newer than the one this SDK targets. See
    https://github.com/open-telemetry/opentelemetry-configuration/blob/main/VERSIONING.md

    Raises:
        ConfigurationError: If ``file_format`` is malformed or its major
            version is not supported.
    """
    file_format = data.get("file_format")
    # file_format is required and typed as a string by the schema, which is
    # validated before this runs; guard defensively regardless.
    if not isinstance(file_format, str):
        raise ConfigurationError(
            f"Invalid file_format: expected a version string, "
            f"got {file_format!r}"
        )

    # Drop any pre-release / meta tag, e.g. "1.0-rc.2" -> "1.0".
    version = file_format.split("-", 1)[0]
    parts = version.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except ValueError as exc:
        raise ConfigurationError(
            f"Invalid file_format '{file_format}': expected MAJOR.MINOR "
            f"version numbers"
        ) from exc

    if major != _SUPPORTED_SCHEMA_MAJOR:
        raise ConfigurationError(
            f"Unsupported file_format '{file_format}': this SDK supports "
            f"schema version {_SUPPORTED_SCHEMA_MAJOR}.x"
        )

    if minor > _SUPPORTED_SCHEMA_MINOR:
        _logger.warning(
            "Configuration file_format '%s' has a newer minor version than "
            "this SDK supports (%d.%d); some settings may be ignored.",
            file_format,
            _SUPPORTED_SCHEMA_MAJOR,
            _SUPPORTED_SCHEMA_MINOR,
        )


def _dict_to_model(data: dict[str, Any]) -> OpenTelemetryConfiguration:
    """Convert a parsed config dictionary to the full typed model tree.

    Walks each field's type annotation, recursively converting nested
    dicts to their corresponding dataclass types. The resulting
    ``OpenTelemetryConfiguration`` is fully typed end-to-end, so factory
    functions can rely on typed attribute access (e.g. ``config.sampler``,
    ``config.processors[0].batch.exporter``).

    Args:
        data: Parsed configuration dictionary.

    Returns:
        OpenTelemetryConfiguration instance.

    Raises:
        TypeError: If data doesn't match expected structure.
        ValueError: If values are invalid.
    """
    try:
        return _dict_to_dataclass(data, OpenTelemetryConfiguration)
    except TypeError as exc:
        raise TypeError(
            f"Configuration structure is invalid. "
            f"Check that all required fields are present and correctly typed: {exc}"
        ) from exc
