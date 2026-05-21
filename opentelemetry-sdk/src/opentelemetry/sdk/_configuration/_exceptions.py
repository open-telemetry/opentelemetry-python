# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


class ConfigurationError(Exception):
    """Raised when configuration loading, parsing, validation, or instantiation fails.

    This includes errors from:
    - File not found or inaccessible
    - Invalid YAML/JSON syntax
    - Schema validation failures
    - Environment variable substitution errors
    - Missing required SDK extensions (e.g., propagator packages not installed)
    """
