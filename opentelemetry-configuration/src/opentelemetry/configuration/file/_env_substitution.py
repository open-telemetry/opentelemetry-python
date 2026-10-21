# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Environment variable substitution for configuration files."""

import os
import re

from opentelemetry.configuration._exceptions import ConfigurationError

# SUBSTITUTION-REF: ``${`` followed by at least one character other than ``}``,
# then ``}``. The content is validated against ENV-SUBSTITUTION separately.
_SUBSTITUTION_REF = re.compile(r"\$\{([^}]+)\}")

# ENV-SUBSTITUTION: an env var name, optionally followed by ``:-default``.
_ENV_SUBSTITUTION = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?::-(.*))?", re.DOTALL)

_ENV_PREFIX = "env:"


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

    - ${VAR} / ${env:VAR}: Substitute with environment variable VAR, or an
      empty value if VAR is not set.
    - ${VAR:-default} / ${env:VAR:-default}: Substitute with VAR if it is set
      and non-empty, otherwise use default value.
    - $$: Escape sequence for literal $.

    Escape sequences are identified first, scanning left to right, and a ``$``
    produced by an escape is never part of a substitution reference. For
    example ``$${VAR}`` resolves to ``${VAR}``, and
    ``${VAR:-$${VAR}}`` resolves to ``${VAR:-${VAR}}`` because neither
    ``${VAR:-`` nor ``{VAR}}`` is a reference on its own. Substituted values
    are inserted verbatim and never re-scanned.

    Per the declarative configuration specification, a referenced environment
    variable that is not set and has no default is replaced with an empty
    value (which the YAML parser then interprets as null). This matches the
    behavior of the Java and Node.js implementations and lets configuration
    files be shared across languages.

    Args:
        text: A configuration value with potential ${VAR} placeholders.

    Returns:
        The configuration value with environment variables substituted.

    Raises:
        ConfigurationError: If the value contains a substitution reference
            that is not a valid env var reference, e.g. ``${VAR:?error}``,
            ``${1VAR}`` or one with an unsupported prefix like ``${sys:x}``.

    Examples:
        >>> os.environ["SERVICE_NAME"] = "my-service"
        >>> substitute_env_vars("${SERVICE_NAME}")
        'my-service'
        >>> substitute_env_vars("${env:SERVICE_NAME}")
        'my-service'
        >>> substitute_env_vars("${MISSING:-default}")
        'default'
        >>> substitute_env_vars("$$100")
        '$100'
    """

    def replace_ref(match: re.Match[str]) -> str:
        content = match.group(1)
        env_match = _ENV_SUBSTITUTION.fullmatch(content)
        # Try the unprefixed form first so ``${VAR:-default}`` is not read as
        # prefix ``VAR``, and ``${env:-x}`` is the variable ``env``.
        if env_match is None and content.startswith(_ENV_PREFIX):
            env_match = _ENV_SUBSTITUTION.fullmatch(content[len(_ENV_PREFIX) :])
        if env_match is None:
            raise ConfigurationError(
                f"Invalid substitution reference {match.group(0)!r}: expected "
                "${NAME}, ${NAME:-default}, ${env:NAME} or ${env:NAME:-default}"
            )

        var_name, default_value = env_match.groups()
        value = os.environ.get(var_name)

        if not value and default_value is not None:
            # The default applies when the variable is unset or empty.
            return default_value

        # Substitution runs on an already-parsed configuration value, so the
        # result cannot inject new YAML structure regardless of its contents
        # (a newline in the value stays a literal character within this one
        # value). Type interpretation for standalone references is handled by
        # the loader, which re-resolves the node tag after substitution.
        return value or ""

    # ``str.split`` finds ``$$`` escapes left to right without overlap, so
    # references are only matched within the text between escapes.
    return "$".join(_SUBSTITUTION_REF.sub(replace_ref, segment) for segment in text.split("$$"))
