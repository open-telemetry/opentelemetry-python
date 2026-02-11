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

"""Environment variable substitution for configuration files."""

import logging
import os
import re

_logger = logging.getLogger(__name__)


class EnvSubstitutionError(Exception):
    """Raised when environment variable substitution fails.

    This occurs when a ${VAR} reference is found but the environment
    variable is not set and no default value is provided.
    """


def substitute_env_vars(text: str) -> str:
    """Substitute environment variables in configuration text.

    Supports the following syntax:
    - ${VAR}: Substitute with environment variable VAR. Raises error if not found.
    - ${VAR:-default}: Substitute with VAR if set, otherwise use default value.
    - $$: Escape sequence for literal $.

    Args:
        text: Configuration text with potential ${VAR} placeholders.

    Returns:
        Text with environment variables substituted.

    Raises:
        EnvSubstitutionError: If a required environment variable is not found.

    Examples:
        >>> os.environ['SERVICE_NAME'] = 'my-service'
        >>> substitute_env_vars('name: ${SERVICE_NAME}')
        'name: my-service'
        >>> substitute_env_vars('name: ${MISSING:-default}')
        'name: default'
        >>> substitute_env_vars('price: $$100')
        'price: $100'
    """
    # First, handle escape sequences by temporarily replacing $$
    # Use a placeholder that's unlikely to appear in config files
    dollar_placeholder = "\x00DOLLAR\x00"
    text = text.replace("$$", dollar_placeholder)

    # Pattern matches: ${VAR_NAME} or ${VAR_NAME:-default_value}
    # Variable names must start with letter or underscore, followed by alphanumerics or underscores
    pattern = r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}"

    def replace_var(match) -> str:
        var_name = match.group(1)
        has_default = match.group(2) is not None
        default_value = match.group(3) if has_default else None

        value = os.environ.get(var_name)

        if value is None:
            if has_default:
                return default_value or ""
            _logger.error(
                "Environment variable '%s' not found and no default provided",
                var_name,
            )
            raise EnvSubstitutionError(
                f"Environment variable '{var_name}' not found and no default provided"
            )

        return value

    # Perform substitution
    text = re.sub(pattern, replace_var, text)

    # Restore escaped dollar signs
    text = text.replace(dollar_placeholder, "$")

    return text
