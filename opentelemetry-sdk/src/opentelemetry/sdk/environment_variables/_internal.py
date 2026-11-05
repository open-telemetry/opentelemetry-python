# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Reading of the environment variables that carry a boolean.

The specification writes a boolean environment variable as the literal
``true`` or ``false``, and asks an SDK to warn and fall back to the default
rather than fail when it reads anything else. This module holds the one
function that applies that rule, so every boolean variable the SDK reads
behaves the same way.
"""

from logging import getLogger
from os import environ

_logger = getLogger(__name__)


def parse_boolean_environment_variable(environment_variable: str, default: bool = False) -> bool:
    """Read one environment variable as a boolean.

    Surrounding whitespace is stripped and the comparison ignores case, so
    ``" TRUE "`` reads as true. The variable is read at each call rather than
    cached, so a change made after import is picked up.

    Args:
        environment_variable: The name of the variable to read.
        default: What to return when the variable is unset, and when it holds
            something other than ``true`` or ``false``.

    Returns:
        ``True`` for ``true``, ``False`` for ``false``, and ``default``
        otherwise. An unparsable value is logged at ``WARNING`` level and
        nothing is raised, so a typo in the environment leaves the SDK
        running on its default.
    """
    value = environ.get(environment_variable)
    if value is None:
        return default

    match value.strip().lower():
        case "true":
            return True
        case "false":
            return False
        case _:
            _logger.warning(
                "Invalid value for %s: %r. Expected 'true' or 'false'.",
                environment_variable,
                value,
            )
            return default
