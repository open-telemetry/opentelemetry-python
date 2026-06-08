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


class MissingDependencyError(ConfigurationError):
    """Raised when an optional dependency is not installed."""

    def __init__(
        self,
        package: str,
        feature: str | None = None,
        install_name: str | None = None,
        extras: str | None = None,
    ) -> None:
        self.package = package
        self.feature = feature
        self.install_name = install_name or package
        self.extras = extras

        if extras:
            install_cmd = f"pip install '{self.install_name}[{extras}]'"
        else:
            install_cmd = f"pip install {self.install_name}"

        if feature:
            message = (
                f"{feature} requires '{package}'. "
                f"Install it with: {install_cmd}"
            )
        else:
            message = (
                f"'{package}' is required but not installed. "
                f"Install it with: {install_cmd}"
            )

        super().__init__(message)
