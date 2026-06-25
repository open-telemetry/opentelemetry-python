# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""OpenTelemetry SDK Declarative Configuration.

This package implements the OpenTelemetry declarative configuration
specification for the Python SDK. Load a YAML or JSON configuration file
(or build a configuration model programmatically) and apply it to the
process-global SDK providers.

The standard activation path is the ``OTEL_CONFIG_FILE`` environment
variable, which the SDK's configurator picks up automatically. For
programmatic use:

>>> from opentelemetry.sdk.configuration import (
...     load_config_file, configure_sdk,
... )
>>> config = load_config_file("otel-config.yaml")
>>> configure_sdk(config)

Construct a configuration programmatically and apply it:

>>> from opentelemetry.sdk.configuration import (
...     OpenTelemetryConfiguration, configure_sdk,
... )
>>> configure_sdk(OpenTelemetryConfiguration(file_format="1.0-rc.1"))

Loading from a file requires the optional ``[file-configuration]`` extras
(``pyyaml`` and ``jsonschema``). ``configure_sdk`` itself has no extra
dependencies: callers that construct an ``OpenTelemetryConfiguration``
directly can use it without installing the extras.

This package is **experimental**. The API surface, type names, and
behaviour may change between minor versions.
"""

from __future__ import annotations

import os

from opentelemetry.sdk.configuration._exceptions import ConfigurationError
from opentelemetry.sdk.configuration._sdk import configure_sdk
from opentelemetry.sdk.configuration.models import OpenTelemetryConfiguration


def load_config_file(
    file_path: str | os.PathLike[str],
) -> OpenTelemetryConfiguration:
    """Load and parse an OpenTelemetry configuration file.

    Thin wrapper that defers importing the file loader until first call so
    the optional ``[file-configuration]`` extras (``pyyaml``, ``jsonschema``)
    are not required just to import this module. See
    :func:`opentelemetry.sdk.configuration.file._loader.load_config_file`
    for the full behaviour and error contract.
    """
    # pylint: disable=import-outside-toplevel
    from opentelemetry.sdk.configuration.file._loader import (  # noqa: PLC0415
        load_config_file as _load_config_file,
    )

    return _load_config_file(file_path)


__all__ = [
    "ConfigurationError",
    "OpenTelemetryConfiguration",
    "configure_sdk",
    "load_config_file",
]
