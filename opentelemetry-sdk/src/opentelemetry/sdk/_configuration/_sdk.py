# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Top-level orchestrator for declarative SDK configuration.

Takes a parsed ``OpenTelemetryConfiguration`` and applies it by calling
each per-signal ``configure_*`` factory in order. This is the single
entry point for "apply this config" on the declarative path.
"""

from __future__ import annotations

import logging

from opentelemetry.sdk._configuration._logger_provider import (
    configure_logger_provider,
)
from opentelemetry.sdk._configuration._meter_provider import (
    configure_meter_provider,
)
from opentelemetry.sdk._configuration._propagator import configure_propagator
from opentelemetry.sdk._configuration._resource import create_resource
from opentelemetry.sdk._configuration._instrumentation import (
    configure_instrumentation,
)
from opentelemetry.sdk._configuration._tracer_provider import (
    configure_tracer_provider,
)
from opentelemetry.sdk._configuration.models import OpenTelemetryConfiguration

_logger = logging.getLogger(__name__)


def configure_sdk(config: OpenTelemetryConfiguration) -> None:
    """Configure the global SDK from a parsed declarative configuration.

    Builds a :class:`Resource` from ``config.resource`` and applies it to
    each signal provider. Sets the global tracer provider, meter provider,
    logger provider, and text map propagator from their respective config
    sections. Sections absent from the config (``None``) leave the
    corresponding global untouched — matching the spec's "noop default"
    behavior.

    Honors the top-level ``disabled`` flag: when true, no globals are set.

    Args:
        config: Parsed ``OpenTelemetryConfiguration`` (typically from
            ``load_config_file``).

    Example:
        >>> from opentelemetry.sdk._configuration.file import (
        ...     load_config_file, configure_sdk,
        ... )
        >>> config = load_config_file("otel-config.yaml")
        >>> configure_sdk(config)
    """
    if config.disabled:
        _logger.warning(
            "Declarative configuration has disabled=true; skipping SDK setup."
        )
        return

    resource = create_resource(config.resource)
    configure_tracer_provider(config.tracer_provider, resource)
    configure_meter_provider(config.meter_provider, resource)
    configure_logger_provider(config.logger_provider, resource)
    configure_propagator(config.propagator)
    configure_instrumentation(config.instrumentation_development)
