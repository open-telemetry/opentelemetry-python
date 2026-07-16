# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Environment variable substitution for configuration files."""

import os
import re


def substitute_env_vars(text: str) -> str:
    """Substitute environment variables in configuration text.

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
        text: Configuration text with potential ${VAR} placeholders.

    Returns:
        Text with environment variables substituted.

    Examples:
        >>> os.environ['SERVICE_NAME'] = 'my-service'
        >>> substitute_env_vars('name: ${SERVICE_NAME}')
        'name: my-service'
        >>> substitute_env_vars('name: ${MISSING:-default}')
        'name: default'
        >>> substitute_env_vars('price: $$100')
        'price: $100'
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
            return (default_value or "") if has_default else ""

        # Per spec: "It MUST NOT be possible to inject YAML structures by
        # environment variables." Newlines are the primary injection vector —
        # a value like "legit\nmalicious_key: val" would create extra YAML
        # keys if substituted verbatim. Wrap such values in a YAML
        # double-quoted scalar so the newline is treated as literal text.
        # Simple values (no newlines) are returned as-is so that YAML type
        # coercion still applies per spec ("Node types MUST be interpreted
        # after environment variable substitution takes place").
        if "\n" in value or "\r" in value:
            escaped = (
                value.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t")
            )
            return f'"{escaped}"'
        return value

    return re.sub(pattern, replace_var, text)
