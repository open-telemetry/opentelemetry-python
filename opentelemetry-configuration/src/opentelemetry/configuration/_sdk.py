# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Top-level orchestrator for declarative SDK configuration.

Takes a parsed ``OpenTelemetryConfiguration`` and applies it by calling
each per-signal ``configure_*`` factory in order. This is the single
entry point for "apply this config" on the declarative path.
"""

from __future__ import annotations

from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING, getLogger

from opentelemetry.configuration._logger_provider import (
    configure_logger_provider,
)
from opentelemetry.configuration._meter_provider import (
    configure_meter_provider,
)
from opentelemetry.configuration._propagator import configure_propagator
from opentelemetry.configuration._resource import create_resource
from opentelemetry.configuration._tracer_provider import (
    configure_tracer_provider,
)
from opentelemetry.configuration.instrumentation import (
    configure_instrumentation,
)
from opentelemetry.configuration.models import (
    OpenTelemetryConfiguration,
    SeverityNumber,
)

_logger = getLogger(__name__)

# Maps OTel SeverityNumber groups to Python logging levels.
# The numbered variants (debug2, info3, …) are sub-levels within the same
# Python tier, so they collapse to the same level constant.
_SEVERITY_TO_LOGGING_LEVEL: dict[SeverityNumber, int] = {
    SeverityNumber.trace: DEBUG,
    SeverityNumber.trace2: DEBUG,
    SeverityNumber.trace3: DEBUG,
    SeverityNumber.trace4: DEBUG,
    SeverityNumber.debug: DEBUG,
    SeverityNumber.debug2: DEBUG,
    SeverityNumber.debug3: DEBUG,
    SeverityNumber.debug4: DEBUG,
    SeverityNumber.info: INFO,
    SeverityNumber.info2: INFO,
    SeverityNumber.info3: INFO,
    SeverityNumber.info4: INFO,
    SeverityNumber.warn: WARNING,
    SeverityNumber.warn2: WARNING,
    SeverityNumber.warn3: WARNING,
    SeverityNumber.warn4: WARNING,
    SeverityNumber.error: ERROR,
    SeverityNumber.error2: ERROR,
    SeverityNumber.error3: ERROR,
    SeverityNumber.error4: ERROR,
    SeverityNumber.fatal: CRITICAL,
    SeverityNumber.fatal2: CRITICAL,
    SeverityNumber.fatal3: CRITICAL,
    SeverityNumber.fatal4: CRITICAL,
}


def configure_sdk(config: OpenTelemetryConfiguration) -> None:
    """Configure the global SDK from a parsed declarative configuration.

    Builds a :class:`Resource` from ``config.resource`` and applies it to
    each signal provider. Sets the global tracer provider, meter provider,
    logger provider, and text map propagator from their respective config
    sections. Sections absent from the config (``None``) leave the
    corresponding global untouched — matching the spec's "noop default"
    behavior.

    Honors the top-level ``disabled`` flag: when true, no globals are set.
    The ``log_level`` field, when present, is applied to the internal
    ``opentelemetry`` logger regardless of ``disabled`` — it configures
    SDK self-diagnostics, not telemetry emission.

    Args:
        config: Parsed ``OpenTelemetryConfiguration`` (typically from
            ``load_config_file``).

    Example:
        >>> from opentelemetry.configuration.file import (
        ...     load_config_file, configure_sdk,
        ... )
        >>> config = load_config_file("otel-config.yaml")
        >>> configure_sdk(config)
    """
    if config.log_level is not None:
        level = _SEVERITY_TO_LOGGING_LEVEL.get(config.log_level, INFO)
        getLogger("opentelemetry").setLevel(level)

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
