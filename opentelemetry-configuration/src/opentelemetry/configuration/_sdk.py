# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Top-level orchestrator for declarative SDK configuration.

``create_sdk`` implements the configuration spec's stateless Create
operation: it interprets a parsed ``OpenTelemetryConfiguration`` and returns
the top level SDK components without touching any global state.
``configure_sdk`` creates the components and only then installs them as the
process global providers and propagator.
"""

from __future__ import annotations

from dataclasses import dataclass
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING, getLogger

from opentelemetry import metrics, trace
from opentelemetry._logs import (
    LoggerProvider,
    NoOpLoggerProvider,
    set_logger_provider,
)
from opentelemetry.configuration._logger_provider import (
    create_logger_provider,
)
from opentelemetry.configuration._meter_provider import (
    create_meter_provider,
)
from opentelemetry.configuration._propagator import create_propagator
from opentelemetry.configuration._resource import create_resource
from opentelemetry.configuration._tracer_provider import (
    create_tracer_provider,
)
from opentelemetry.configuration.file._loader import (
    _validate_file_format,
)
from opentelemetry.configuration.instrumentation import (
    configure_instrumentation,
)
from opentelemetry.configuration.models import (
    OpenTelemetryConfiguration,
    SeverityNumber,
)
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.sdk._logs import LoggerProvider as SdkLoggerProvider
from opentelemetry.sdk.metrics import MeterProvider as SdkMeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider as SdkTracerProvider

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


@dataclass(frozen=True)
class SdkComponents:
    """Top level SDK components created from a declarative configuration.

    Providers for sections omitted from the configuration and all providers
    when the configuration sets ``disabled: true`` are the API no-op
    implementations.
    """

    tracer_provider: trace.TracerProvider
    meter_provider: metrics.MeterProvider
    logger_provider: LoggerProvider
    propagator: TextMapPropagator
    resource: Resource

    def shutdown(self) -> None:
        """Shut down every SDK provider; no-op providers are skipped."""
        _shutdown_providers([self.tracer_provider, self.meter_provider, self.logger_provider])


def _shutdown_providers(
    providers: list[trace.TracerProvider | metrics.MeterProvider | LoggerProvider],
) -> None:
    """Shut down SDK providers, logging rather than raising on failure."""
    for provider in providers:
        if not isinstance(provider, (SdkTracerProvider, SdkMeterProvider, SdkLoggerProvider)):
            continue
        try:
            provider.shutdown()
        except Exception:  # pylint: disable=broad-except
            _logger.exception("Failed to shut down %s", type(provider).__name__)


def create_sdk(config: OpenTelemetryConfiguration) -> SdkComponents:
    """Create SDK components from a declarative configuration model.

    Implements the configuration spec's Create operation. This is stateless:
    no global provider, propagator, or logger level is modified, so the
    caller decides whether and how to install the returned components.

    Sections omitted from ``config`` yield the API no-op provider (and an
    empty composite propagator), per the configuration schema's "If omitted,
    a noop ... is used". When ``config.disabled`` is true, all providers are
    no-op but the configured propagator and resource are still created, so
    context keeps propagating through the process.

    The SDK's own metrics (from providers, processors, and OTLP exporters)
    are recorded through the created meter provider, so creation never reads
    the global MeterProvider.

    If creating any component fails, providers already created are shut
    down before the error is re-raised.

    Args:
        config: Configuration model, from ``load_config`` or built in code.

    Returns:
        The created tracer, meter, and logger providers, propagator, and
        resource.

    Raises:
        ConfigurationError: If the configuration is invalid or a component
            cannot be created.
    """
    _validate_file_format(config.file_format)

    resource = create_resource(config.resource)
    propagator = create_propagator(config.propagator)

    if config.disabled:
        _logger.warning("Declarative configuration has disabled=true; using no-op tracer, meter and logger providers.")
        return SdkComponents(
            tracer_provider=trace.NoOpTracerProvider(),
            meter_provider=metrics.NoOpMeterProvider(),
            logger_provider=NoOpLoggerProvider(),
            propagator=propagator,
            resource=resource,
        )

    global_attribute_limits = config.attribute_limits
    created: list[trace.TracerProvider | metrics.MeterProvider | LoggerProvider] = []
    try:
        # Created first so the other providers record the SDK's own metrics
        # through it rather than reading the global MeterProvider.
        meter_provider: metrics.MeterProvider = metrics.NoOpMeterProvider()
        if config.meter_provider is not None:
            meter_provider = create_meter_provider(config.meter_provider, resource)
            created.append(meter_provider)

        tracer_provider: trace.TracerProvider = trace.NoOpTracerProvider()
        if config.tracer_provider is not None:
            tracer_provider = create_tracer_provider(
                config.tracer_provider,
                resource,
                global_attribute_limits,
                meter_provider=meter_provider,
            )
            created.append(tracer_provider)

        logger_provider: LoggerProvider = NoOpLoggerProvider()
        if config.logger_provider is not None:
            logger_provider = create_logger_provider(
                config.logger_provider,
                resource,
                global_attribute_limits,
                meter_provider=meter_provider,
            )
            created.append(logger_provider)
    except Exception:
        _shutdown_providers(created)
        raise

    return SdkComponents(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        logger_provider=logger_provider,
        propagator=propagator,
        resource=resource,
    )


def configure_sdk(config: OpenTelemetryConfiguration) -> SdkComponents:
    """Configure the global SDK from a declarative configuration model.

    Creates every component with :func:`create_sdk` before any global is
    touched, so a creation error leaves the global providers and propagator
    unchanged. On success, installs the tracer, meter, and logger providers
    (no-op ones included, so the API never falls back to
    environment-selected providers) and the text map propagator as globals,
    applies ``log_level`` to the internal ``opentelemetry`` logger, and,
    unless the configuration is disabled, activates the instrumentation
    listed under ``instrumentation/development``.

    Args:
        config: Configuration model, from ``load_config`` or built in code.

    Returns:
        The installed SDK components, e.g. for shutting them down.

    Raises:
        ConfigurationError: If the configuration is invalid or a component
            cannot be created.

    Example:
        >>> from opentelemetry.configuration import configure_sdk, load_config
        >>> components = configure_sdk(load_config("otel-config.yaml"))
    """
    components = create_sdk(config)

    trace.set_tracer_provider(components.tracer_provider)
    metrics.set_meter_provider(components.meter_provider)
    set_logger_provider(components.logger_provider)
    set_global_textmap(components.propagator)

    if config.log_level is not None:
        level = _SEVERITY_TO_LOGGING_LEVEL.get(config.log_level, INFO)
        getLogger("opentelemetry").setLevel(level)

    if not config.disabled:
        configure_instrumentation(config.instrumentation_development)

    return components
