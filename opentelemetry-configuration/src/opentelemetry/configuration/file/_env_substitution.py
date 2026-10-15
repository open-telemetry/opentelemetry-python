# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Environment variable substitution for configuration files."""

import os
import re


def substitute_env_vars(text: str) -> str:
    """Substitute environment variables within a configuration value.

    A configuration value is a single value from the parsed configuration file
    (the value of one key or one list item), never a key, a comment, or a whole
    mapping/list. Substitution is applied per configuration value after the
    file has been parsed, so comments and mapping keys are never touched.

    For example, given the YAML::

        service_name: ${SERVICE_NAME}
        endpoint: http://${HOST}:${PORT}

    the configuration values are ``${SERVICE_NAME}`` and
    ``http://${HOST}:${PORT}``; this function is called once with each, and
    never with the keys ``service_name`` or ``endpoint``.

    Supports the following syntax:

    - ${VAR}: Substitute with environment variable VAR, or an empty value if
      VAR is not set.
    - ${VAR:-default}: Substitute with VAR if set, otherwise use default value.
    - $$: Escape sequence for literal $.

    Per the declarative configuration specification, a referenced environment
    variable that is not set and has no default is replaced with an empty
    value (which the YAML parser then interprets as null). This matches the
    behavior of the Java and Node.js implementations and lets configuration
    files be shared across languages.

    Args:
        text: A configuration value with potential ${VAR} placeholders.

    Returns:
        The configuration value with environment variables substituted.

    Examples:
        >>> os.environ["SERVICE_NAME"] = "my-service"
        >>> substitute_env_vars("${SERVICE_NAME}")
        'my-service'
        >>> substitute_env_vars("${MISSING:-default}")
        'default'
        >>> substitute_env_vars("$$100")
        '$100'
    """
    # Pattern matches $$ (escape sequence) or ${VAR_NAME} / ${VAR_NAME:-default_value}
    # Handling both in a single pass ensures $$ followed by ${VAR} works correctly
    pattern = r"\$\$|\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}"

    def replace_var(match) -> str:
        if match.group(1) is None:
            # Matched $$, return literal $
            return "$"

        var_name = match.group(1)
        has_default = match.group(2) is not None
        default_value = match.group(3) if has_default else None

        value = os.environ.get(var_name)

        if value is None:
            # An unset variable is replaced with its default if one is
            # provided, otherwise with an empty value, per the spec.
            return default_value or ""

        # Substitution runs on an already-parsed configuration value, so the
        # result cannot inject new YAML structure regardless of its contents
        # (a newline in the value stays a literal character within this one
        # value). Type interpretation for standalone references is handled by
        # the loader, which re-resolves the node tag after substitution.
        return value

    return re.sub(pattern, replace_var, text)
