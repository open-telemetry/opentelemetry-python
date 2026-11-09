# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
The OpenTelemetry Instrumentation Configuration API gives instrumentation
libraries read access to the ``instrumentation`` node of a declarative
configuration file.

The :class:`.ConfigProvider` holds a :class:`.ConfigProperties`, a typed read
view over that node. An instrumentation library reads its own configuration
during initialization through the global provider::

    from opentelemetry._configuration import get_config_provider

    properties = get_config_provider().get_instrumentation_config()
    example = properties.get_config("example")
    if example is not None:
        enabled = example.get_bool("enabled")

The provider is installed by whatever applies a declarative configuration, such
as ``opentelemetry.configuration.configure_sdk`` in the
``opentelemetry-configuration`` package. Until one is installed,
:func:`.get_config_provider` returns a :class:`.ProxyConfigProvider` exposing
empty configuration, so an instrumentation library never needs the SDK or a
configuration file to be present.

``ConfigProvider`` is at Development stability in the specification
(https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/configuration/api.md),
which is why this module carries a leading underscore.
"""

from opentelemetry._configuration._internal import (
    ConfigProperties,
    ConfigProvider,
    NoOpConfigProvider,
    ProxyConfigProvider,
    get_config_provider,
    set_config_provider,
)

__all__ = [
    "ConfigProperties",
    "ConfigProvider",
    "NoOpConfigProvider",
    "ProxyConfigProvider",
    "get_config_provider",
    "set_config_provider",
]
