# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Public API for the OpenTelemetry SDK's declarative configuration.

Load a parsed configuration from a YAML/JSON file and apply it to the
process-global SDK providers:

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
dependencies — callers that construct an ``OpenTelemetryConfiguration``
directly can use it without installing the extras.
"""

from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration._sdk import configure_sdk
from opentelemetry.sdk._configuration.models import OpenTelemetryConfiguration


def __getattr__(name: str):
    # ``load_config_file`` lives behind the optional file-configuration
    # extras (pyyaml, jsonschema). Resolve it lazily so importing this
    # module does not require those extras for callers that only use
    # ``configure_sdk`` with a programmatically built configuration.
    if name == "load_config_file":
        # pylint: disable=import-outside-toplevel
        from opentelemetry.sdk._configuration.file._loader import (  # noqa: PLC0415
            load_config_file,
        )

        return load_config_file
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ``load_config_file`` is exposed via ``__getattr__`` rather than a module-level
# binding so the file-configuration extras stay optional. Pylint's static
# analysis doesn't see ``__getattr__`` and flags it as undefined; suppress.
__all__ = [
    "ConfigurationError",
    "OpenTelemetryConfiguration",
    "configure_sdk",
    "load_config_file",  # pylint: disable=undefined-all-variable
]
