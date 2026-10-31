# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
#

# pylint: disable=too-many-lines
"""
OpenTelemetry SDK Configurator for Easy Instrumentation with Distros

This module builds and installs the three global providers from environment
variables alone, so that an application needs no setup code of its own. It is
what the ``opentelemetry-instrument`` command runs, through the
``opentelemetry_configurator`` entry point, and what a distribution subclasses
when it wants different defaults.

Each component is named in an environment variable and resolved through an
entry point group: an exporter through ``opentelemetry_traces_exporter`` and
its metric and log counterparts, a sampler through
``opentelemetry_traces_sampler``, an id generator through
``opentelemetry_id_generator``. A name that no entry point provides is a
``RuntimeError``, except where a function below says it logs a warning and
falls back instead.

Everything here is private to the SDK. A distribution should subclass
``_OTelSDKConfigurator`` rather than call these functions, and the names may
change without a deprecation period.
"""

from __future__ import annotations

import logging
import logging.config
import os
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from os import environ
from typing import Any, Literal, Protocol

from opentelemetry._logs import set_logger_provider
from opentelemetry.environment_variables import (
    OTEL_LOGS_EXPORTER,
    OTEL_METRICS_EXPORTER,
    OTEL_PYTHON_ID_GENERATOR,
    OTEL_TRACES_EXPORTER,
)
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk._logs import (
    LoggerProvider,
    LoggingHandler,
    LogRecordProcessor,
)
from opentelemetry.sdk._logs._internal import _LoggerConfiguratorT
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    LogRecordExporter,
)
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED,
    OTEL_CONFIG_FILE,
    OTEL_EXPORTER_OTLP_LOGS_PROTOCOL,
    OTEL_EXPORTER_OTLP_METRICS_PROTOCOL,
    OTEL_EXPORTER_OTLP_PROTOCOL,
    OTEL_EXPORTER_OTLP_TRACES_PROTOCOL,
    OTEL_PYTHON_LOGGER_CONFIGURATOR,
    OTEL_PYTHON_METER_CONFIGURATOR,
    OTEL_PYTHON_TRACER_CONFIGURATOR,
    OTEL_TRACES_SAMPLER,
    OTEL_TRACES_SAMPLER_ARG,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal import _MeterConfiguratorT
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    MetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Attributes, Resource
from opentelemetry.sdk.trace import (
    SpanProcessor,
    TracerProvider,
    _TracerConfiguratorT,
)
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.id_generator import IdGenerator
from opentelemetry.sdk.trace.sampling import Sampler
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import set_tracer_provider
from opentelemetry.util._importlib_metadata import entry_points

_EXPORTER_OTLP = "otlp"
_EXPORTER_OTLP_PROTO_GRPC = "otlp_proto_grpc"
_EXPORTER_OTLP_PROTO_HTTP = "otlp_proto_http"

_EXPORTER_BY_OTLP_PROTOCOL = {
    "grpc": _EXPORTER_OTLP_PROTO_GRPC,
    "http/protobuf": _EXPORTER_OTLP_PROTO_HTTP,
}

_EXPORTER_ENV_BY_SIGNAL_TYPE = {
    "traces": OTEL_TRACES_EXPORTER,
    "metrics": OTEL_METRICS_EXPORTER,
    "logs": OTEL_LOGS_EXPORTER,
}

_PROTOCOL_ENV_BY_SIGNAL_TYPE = {
    "traces": OTEL_EXPORTER_OTLP_TRACES_PROTOCOL,
    "metrics": OTEL_EXPORTER_OTLP_METRICS_PROTOCOL,
    "logs": OTEL_EXPORTER_OTLP_LOGS_PROTOCOL,
}

_RANDOM_ID_GENERATOR = "random"
_DEFAULT_ID_GENERATOR = _RANDOM_ID_GENERATOR

_OTEL_SAMPLER_ENTRY_POINT_GROUP = "opentelemetry_traces_sampler"

_logger = logging.getLogger(__name__)

ExporterArgsMap = Mapping[
    type[SpanExporter] | type[MetricExporter] | type[MetricReader] | type[LogRecordExporter],
    Mapping[str, Any],
]


class _ConfigurationExporterSpanProcessorT(Protocol):
    """What ``_init_tracing`` accepts in place of ``BatchSpanProcessor``.

    A distribution passes something matching this to wrap each configured
    span exporter in a processor of its own choosing.
    """

    def __call__(self, span_exporter: SpanExporter, *args, **kwargs) -> SpanProcessor:
        """Wrap one span exporter in a span processor.

        Args:
            span_exporter: The exporter to wrap, already constructed.
            *args: Extra positional arguments. ``_init_tracing`` passes none.
            **kwargs: Extra keyword arguments. ``_init_tracing`` passes none.

        Returns:
            The processor to register on the tracer provider.
        """
        ...  # pylint: disable=unnecessary-ellipsis


class _ConfigurationExporterLogRecordProcessorT(Protocol):
    """What ``_init_logging`` accepts in place of ``BatchLogRecordProcessor``.

    A distribution passes something matching this to wrap each configured log
    record exporter in a processor of its own choosing.
    """

    def __call__(self, exporter: LogRecordExporter, *args, **kwargs) -> LogRecordProcessor:
        """Wrap one log record exporter in a log record processor.

        Args:
            exporter: The exporter to wrap, already constructed.
            *args: Extra positional arguments. ``_init_logging`` passes none.
            **kwargs: Extra keyword arguments. ``_init_logging`` passes none.

        Returns:
            The processor to register on the logger provider.
        """
        ...  # pylint: disable=unnecessary-ellipsis


def _import_config_components(selected_components: Sequence[str], entry_point_name: str) -> list[tuple[str, type]]:
    """Load each named component from one entry point group.

    Args:
        selected_components: The entry point names to load, in order. Each
            one is looked up as it is given, so a caller that accepts
            whitespace around a name has to strip it first.
        entry_point_name: The entry point group to look in, for example
            ``opentelemetry_traces_exporter``.

    Returns:
        One pair per requested name, in the order requested, holding the name
        and the object the entry point loaded. The object is not checked
        against any interface here; the caller does that.

    Raises:
        RuntimeError: If the group does not exist, or if a requested name is
            not in it. A name that resolves to several entry points takes the
            first.
    """
    component_implementations = []

    for selected_component in selected_components:
        try:
            component_implementations.append(
                (
                    selected_component,
                    next(iter(entry_points(group=entry_point_name, name=selected_component))).load(),
                )
            )
        except KeyError:
            raise RuntimeError(f"Requested entry point '{entry_point_name}' not found")

        except StopIteration:
            raise RuntimeError(
                f"Requested component '{selected_component}' not found in entry point '{entry_point_name}'"
            )

    return component_implementations


def _get_sampler() -> str | None:
    """Read the configured sampler name.

    Returns:
        The value of ``OTEL_TRACES_SAMPLER``, or ``None`` when it is unset,
        which leaves the tracer provider on its own default sampler.
    """
    return environ.get(OTEL_TRACES_SAMPLER, None)


def _get_id_generator() -> str:
    """Read the configured id generator name.

    Returns:
        The value of ``OTEL_PYTHON_ID_GENERATOR``, or ``"random"`` when it is
        unset.
    """
    return environ.get(OTEL_PYTHON_ID_GENERATOR, _DEFAULT_ID_GENERATOR)


def _get_tracer_configurator() -> str | None:
    """Read the configured tracer configurator name.

    Returns:
        The value of ``OTEL_PYTHON_TRACER_CONFIGURATOR``, or ``None`` when it
        is unset, which gives every tracer the same configuration.
    """
    return environ.get(OTEL_PYTHON_TRACER_CONFIGURATOR, None)


def _get_meter_configurator() -> str | None:
    """Read the configured meter configurator name.

    Returns:
        The value of ``OTEL_PYTHON_METER_CONFIGURATOR``, or ``None`` when it
        is unset, which gives every meter the same configuration.
    """
    return environ.get(OTEL_PYTHON_METER_CONFIGURATOR, None)


def _get_logger_configurator() -> str | None:
    """Read the configured logger configurator name.

    Returns:
        The value of ``OTEL_PYTHON_LOGGER_CONFIGURATOR``, or ``None`` when it
        is unset, which gives every logger the same configuration.
    """
    return environ.get(OTEL_PYTHON_LOGGER_CONFIGURATOR, None)


def _get_exporter_entry_point(exporter_name: str, signal_type: Literal["traces", "metrics", "logs"]):
    """Resolve an OTLP exporter name to the entry point of one transport.

    The name ``otlp`` does not name an entry point on its own, because the
    OTLP exporter ships one implementation per transport. The transport is
    taken from the signal-specific protocol variable when it is set, and from
    ``OTEL_EXPORTER_OTLP_PROTOCOL`` otherwise. With neither set, ``otlp``
    becomes the gRPC implementation.

    A name that already states the transport, ``otlp_proto_grpc`` or
    ``otlp_proto_http``, keeps it. When a protocol variable asks for the other
    transport, the name wins and the disagreement is logged at ``WARNING``
    level.

    Args:
        exporter_name: The exporter name as configured, already stripped.
        signal_type: Which signal this exporter is for, which selects the
            signal-specific protocol variable to read.

    Returns:
        The entry point name to load. A name that is not one of the three
        OTLP spellings is returned unchanged, so this function is safe to
        call on every configured exporter.

    Raises:
        RuntimeError: If ``exporter_name`` is ``otlp`` and the protocol
            variable holds something other than ``grpc`` or
            ``http/protobuf``.
    """
    if exporter_name not in (
        _EXPORTER_OTLP,
        _EXPORTER_OTLP_PROTO_GRPC,
        _EXPORTER_OTLP_PROTO_HTTP,
    ):
        return exporter_name

    # Checking env vars for OTLP protocol (grpc/http).
    otlp_protocol = environ.get(_PROTOCOL_ENV_BY_SIGNAL_TYPE[signal_type]) or environ.get(OTEL_EXPORTER_OTLP_PROTOCOL)

    if not otlp_protocol:
        if exporter_name == _EXPORTER_OTLP:
            return _EXPORTER_OTLP_PROTO_GRPC
        return exporter_name

    otlp_protocol = otlp_protocol.strip()

    if exporter_name == _EXPORTER_OTLP:
        if otlp_protocol not in _EXPORTER_BY_OTLP_PROTOCOL:
            # Invalid value was set by the env var
            raise RuntimeError(f"Unsupported OTLP protocol '{otlp_protocol}' is configured")

        return _EXPORTER_BY_OTLP_PROTOCOL[otlp_protocol]

    # grpc/http already specified by exporter_name, only add a warning in case
    # of a conflict.
    exporter_name_by_env = _EXPORTER_BY_OTLP_PROTOCOL.get(otlp_protocol)
    if exporter_name_by_env and exporter_name != exporter_name_by_env:
        _logger.warning(
            "Conflicting values for %s OTLP exporter protocol, using '%s'",
            signal_type,
            exporter_name,
        )

    return exporter_name


def _get_exporter_names(
    signal_type: Literal["traces", "metrics", "logs"],
) -> list[str]:
    """Read the exporters configured for one signal.

    Args:
        signal_type: Which signal to read, which selects between
            ``OTEL_TRACES_EXPORTER``, ``OTEL_METRICS_EXPORTER`` and
            ``OTEL_LOGS_EXPORTER``.

    Returns:
        The entry point names to load, in the order given, with each OTLP
        name already resolved to a transport. The list is empty when the
        variable is unset, when it is empty, and when it holds the sentinel
        ``none`` in any case with surrounding whitespace, which is how an
        operator turns a signal off.

    Raises:
        RuntimeError: If an ``otlp`` entry is configured and the protocol
            variable holds an unsupported value.
    """
    names = environ.get(_EXPORTER_ENV_BY_SIGNAL_TYPE.get(signal_type, ""))

    if not names or names.lower().strip() == "none":
        return []

    return [_get_exporter_entry_point(_exporter.strip(), signal_type) for _exporter in names.split(",")]


def _init_tracing(
    exporters: dict[str, type[SpanExporter]],
    id_generator: IdGenerator | None = None,
    sampler: Sampler | None = None,
    resource: Resource | None = None,
    exporter_args_map: ExporterArgsMap | None = None,
    span_processors: Sequence[SpanProcessor] | None = None,
    export_span_processor: _ConfigurationExporterSpanProcessorT | None = None,
    tracer_configurator: _TracerConfiguratorT | None = None,
):
    """Build a tracer provider, install it globally and attach the exporters.

    The provider is set as the global one before the processors are added, so
    a tracer taken during this call already belongs to it. The provider is
    installed even when there are no exporters, which is what makes spans
    record without being sent anywhere.

    Args:
        exporters: The span exporter classes to attach, keyed by the entry
            point name they were loaded under. The key is not used; the
            classes are what matter, and each is constructed here.
        id_generator: The generator of trace and span ids, or ``None`` to let
            the provider use its own default.
        sampler: The sampler, or ``None`` to let the provider use its own
            default.
        resource: The resource every span is attributed to, or ``None`` to
            let the provider build one.
        exporter_args_map: Keyword arguments to construct a given exporter
            class with, keyed by the class. A class that is absent is built
            with no arguments. Pass ``None`` for no arguments at all.
        span_processors: Processors to register before the exporting ones, so
            they see a span first. Pass ``None`` for none.
        export_span_processor: What to wrap each exporter in, or ``None`` to
            use ``BatchSpanProcessor``.
        tracer_configurator: The per-scope tracer configuration, or ``None``
            to configure every tracer alike.
    """
    provider = TracerProvider(
        id_generator=id_generator,
        sampler=sampler,
        resource=resource,
        _tracer_configurator=tracer_configurator,
    )
    set_tracer_provider(provider)

    exporter_args_map = exporter_args_map or {}
    export_processor = export_span_processor or BatchSpanProcessor

    span_processors = span_processors or []
    for span_processor in span_processors:
        provider.add_span_processor(span_processor)

    for _, exporter_class in exporters.items():
        exporter_args = exporter_args_map.get(exporter_class, {})
        provider.add_span_processor(export_processor(exporter_class(**exporter_args)))


def _init_metrics(
    exporters_or_readers: dict[str, type[MetricExporter | MetricReader]],
    resource: Resource | None = None,
    exporter_args_map: ExporterArgsMap | None = None,
    meter_configurator: _MeterConfiguratorT | None = None,
):
    """Build a meter provider from the configured exporters and install it.

    The metrics entry point group holds two kinds of thing. A class that is a
    ``MetricReader`` is used as it is, which is how a pull-based exporter
    such as the Prometheus one works. Anything else is treated as a
    ``MetricExporter`` and wrapped in a ``PeriodicExportingMetricReader``,
    which is what makes a push-based exporter run on a timer.

    Args:
        exporters_or_readers: The classes to attach, keyed by the entry point
            name they were loaded under. The key is not used.
        resource: The resource every metric is attributed to, or ``None`` to
            let the provider build one.
        exporter_args_map: Keyword arguments to construct a given class with,
            keyed by the class. A class that is absent is built with no
            arguments. Pass ``None`` for no arguments at all.
        meter_configurator: The per-scope meter configuration, or ``None`` to
            configure every meter alike.
    """
    metric_readers = []

    exporter_args_map = exporter_args_map or {}
    for _, exporter_or_reader_class in exporters_or_readers.items():
        exporter_args = exporter_args_map.get(exporter_or_reader_class, {})
        if issubclass(exporter_or_reader_class, MetricReader):
            metric_readers.append(exporter_or_reader_class(**exporter_args))
        else:
            metric_readers.append(PeriodicExportingMetricReader(exporter_or_reader_class(**exporter_args)))

    provider = MeterProvider(
        resource=resource,
        metric_readers=metric_readers,
        _meter_configurator=meter_configurator,
    )
    set_meter_provider(provider)


# pylint: disable-next=too-many-locals
def _init_logging(
    exporters: dict[str, type[LogRecordExporter]],
    resource: Resource | None = None,
    setup_logging_handler: bool = True,
    exporter_args_map: ExporterArgsMap | None = None,
    log_record_processors: Sequence[LogRecordProcessor] | None = None,
    export_log_record_processor: _ConfigurationExporterLogRecordProcessorT | None = None,
    logger_configurator: _LoggerConfiguratorT | None = None,
):
    """Build a logger provider, install it globally and attach the exporters.

    When ``setup_logging_handler`` is true, a ``LoggingHandler`` is added to
    the root logger of the standard library, which is what sends ordinary
    ``logging`` calls through OpenTelemetry. That path is deprecated in
    favour of the ``opentelemetry-instrumentation-logging`` package, so a
    ``DeprecationWarning`` is raised when it is taken.

    Taking that path also replaces ``logging.config.fileConfig``,
    ``logging.config.dictConfig`` and ``logging.basicConfig`` at module level
    with wrappers that preserve the handler, since each of those would
    otherwise remove it.

    Args:
        exporters: The log record exporter classes to attach, keyed by the
            entry point name they were loaded under. The key is not used.
        resource: The resource every log record is attributed to, or ``None``
            to let the provider build one.
        setup_logging_handler: Whether to attach the handler to the root
            logger, as described above.
        exporter_args_map: Keyword arguments to construct a given exporter
            class with, keyed by the class. A class that is absent is built
            with no arguments. Pass ``None`` for no arguments at all.
        log_record_processors: Processors to register before the exporting
            ones, so they see a record first. Pass ``None`` for none.
        export_log_record_processor: What to wrap each exporter in, or
            ``None`` to use ``BatchLogRecordProcessor``.
        logger_configurator: The per-scope logger configuration, or ``None``
            to configure every logger alike.
    """
    provider = LoggerProvider(resource=resource, _logger_configurator=logger_configurator)
    set_logger_provider(provider)

    exporter_args_map = exporter_args_map or {}
    export_processor = export_log_record_processor or BatchLogRecordProcessor

    log_record_processors = log_record_processors or []
    for log_record_processor in log_record_processors:
        provider.add_log_record_processor(log_record_processor)

    for _, exporter_class in exporters.items():
        exporter_args = exporter_args_map.get(exporter_class, {})
        provider.add_log_record_processor(export_processor(exporter_class(**exporter_args)))

    if setup_logging_handler:
        warnings.warn(
            "The `OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED` environment variable "
            "and the `LoggingHandler` in `opentelemetry-sdk` that it controls are deprecated."
            "Install `opentelemetry-instrumentation-logging` package instead.",
            DeprecationWarning,
        )

        # Add OTel handler
        handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)
        logging.getLogger().addHandler(handler)
        _overwrite_logging_config_fns(handler)


def _overwrite_logging_config_fns(handler: LoggingHandler) -> None:
    """Keep ``handler`` on the root logger across a logging reconfiguration.

    ``logging.config.fileConfig``, ``logging.config.dictConfig`` and
    ``logging.basicConfig`` each replace or clear the handlers of the root
    logger, which would silently stop the OpenTelemetry handler from
    receiving anything. All three are replaced here by wrappers that take the
    handler off before the call and put it back afterwards.

    The replacement is global and permanent for the process, and calling this
    twice wraps the wrappers.

    Args:
        handler: The handler to preserve. It is captured by the wrappers, so
            it stays alive for as long as the ``logging`` module does.
    """
    root = logging.getLogger()

    def wrapper(config_fn: Callable) -> Callable:
        """Wrap one logging configuration function.

        Args:
            config_fn: The function to wrap, one of the three named above.

        Returns:
            A function with the same signature that preserves the handler.
        """

        def overwritten_config_fn(*args, **kwargs):
            """Run the wrapped function with the handler detached.

            The handler is put back in a ``finally`` block, so it survives a
            configuration function that raises. It is only put back when it
            was actually present beforehand, so this does not re-add a
            handler the application had already removed on purpose.

            Args:
                *args: Passed through to the wrapped function.
                **kwargs: Passed through to the wrapped function.
            """
            removed_handler = False
            # We don't want the OTLP handler to be modified or deleted by the logging config functions.
            # So we remove it and then add it back after the function call.
            if handler in root.handlers:
                removed_handler = True
                root.handlers.remove(handler)
            try:
                config_fn(*args, **kwargs)
            finally:
                # Ensure handler is added back if logging function throws exception.
                if removed_handler:
                    root.addHandler(handler)

        return overwritten_config_fn

    logging.config.fileConfig = wrapper(logging.config.fileConfig)
    logging.config.dictConfig = wrapper(logging.config.dictConfig)
    logging.basicConfig = wrapper(logging.basicConfig)


def _import_logger_configurator(
    logger_configurator_name: str | None,
) -> _LoggerConfiguratorT | None:
    """Load the per-scope logger configuration named by ``OTEL_PYTHON_LOGGER_CONFIGURATOR``.

    Args:
        logger_configurator_name: The entry point name in the
            ``_opentelemetry_logger_configurator`` group, or ``None`` or the
            empty string to ask for no configurator. Surrounding whitespace
            is stripped.

    Returns:
        The loaded configurator, or ``None`` when none was asked for and when
        the named one could not be loaded. A failure is logged at ``WARNING``
        level and is never raised, so a broken configurator leaves the SDK
        running with every logger configured alike.
    """
    if not logger_configurator_name:
        return None

    try:
        _, logger_configurator_impl = _import_config_components(
            [logger_configurator_name.strip()],
            "_opentelemetry_logger_configurator",
        )[0]
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _logger.warning(
            "Using default logger configurator. Failed to load logger configurator, %s: %s",
            logger_configurator_name,
            exc,
        )
        return None
    return logger_configurator_impl


def _import_tracer_configurator(
    tracer_configurator_name: str | None,
) -> _TracerConfiguratorT | None:
    """Load the per-scope tracer configuration named by ``OTEL_PYTHON_TRACER_CONFIGURATOR``.

    Args:
        tracer_configurator_name: The entry point name in the
            ``_opentelemetry_tracer_configurator`` group, or ``None`` or the
            empty string to ask for no configurator. Surrounding whitespace
            is stripped.

    Returns:
        The loaded configurator, or ``None`` when none was asked for and when
        the named one could not be loaded. A failure is logged at ``WARNING``
        level and is never raised, so a broken configurator leaves the SDK
        running with every tracer configured alike.
    """
    if not tracer_configurator_name:
        return None

    try:
        _, tracer_configurator_impl = _import_config_components(
            [tracer_configurator_name.strip()],
            "_opentelemetry_tracer_configurator",
        )[0]
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _logger.warning(
            "Using default tracer configurator. Failed to load tracer configurator, %s: %s",
            tracer_configurator_name,
            exc,
        )
        return None
    return tracer_configurator_impl


def _import_meter_configurator(
    meter_configurator_name: str | None,
) -> _MeterConfiguratorT | None:
    """Load the per-scope meter configuration named by ``OTEL_PYTHON_METER_CONFIGURATOR``.

    Args:
        meter_configurator_name: The entry point name in the
            ``_opentelemetry_meter_configurator`` group, or ``None`` or the
            empty string to ask for no configurator. Surrounding whitespace
            is stripped.

    Returns:
        The loaded configurator, or ``None`` when none was asked for and when
        the named one could not be loaded. A failure is logged at ``WARNING``
        level and is never raised, so a broken configurator leaves the SDK
        running with every meter configured alike.
    """
    if not meter_configurator_name:
        return None

    try:
        _, meter_configurator_impl = _import_config_components(
            [meter_configurator_name.strip()],
            "_opentelemetry_meter_configurator",
        )[0]
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _logger.warning(
            "Using default meter configurator. Failed to load meter configurator, %s: %s",
            meter_configurator_name,
            exc,
        )
        return None
    return meter_configurator_impl


def _import_exporters(
    trace_exporter_names: Sequence[str],
    metric_exporter_names: Sequence[str],
    log_exporter_names: Sequence[str],
) -> tuple[
    dict[str, type[SpanExporter]],
    dict[str, type[MetricExporter | MetricReader]],
    dict[str, type[LogRecordExporter]],
]:
    """Load the exporter classes of all three signals and check their types.

    Nothing is constructed here; the classes are returned for the
    ``_init_*`` functions to build.

    Args:
        trace_exporter_names: Entry point names in the
            ``opentelemetry_traces_exporter`` group.
        metric_exporter_names: Entry point names in the
            ``opentelemetry_metrics_exporter`` group. An entry there may be a
            ``MetricExporter`` or a ``MetricReader``, since a pull-based
            exporter is registered as a reader.
        log_exporter_names: Entry point names in the
            ``opentelemetry_logs_exporter`` group.

    Returns:
        Three mappings from entry point name to class, for traces, metrics
        and logs in that order.

    Raises:
        RuntimeError: If a name is not in its group, or if what it loads is
            not of the type that group is supposed to hold.
    """
    trace_exporters = {}
    metric_exporters = {}
    log_exporters = {}

    for (
        exporter_name,
        exporter_impl,
    ) in _import_config_components(trace_exporter_names, "opentelemetry_traces_exporter"):
        if issubclass(exporter_impl, SpanExporter):
            trace_exporters[exporter_name] = exporter_impl
        else:
            raise RuntimeError(f"{exporter_name} is not a trace exporter")

    for (
        exporter_name,
        exporter_impl,
    ) in _import_config_components(metric_exporter_names, "opentelemetry_metrics_exporter"):
        # The metric exporter components may be push MetricExporter or pull exporters which
        # subclass MetricReader directly
        if issubclass(exporter_impl, (MetricExporter, MetricReader)):
            metric_exporters[exporter_name] = exporter_impl
        else:
            raise RuntimeError(f"{exporter_name} is not a metric exporter")

    for (
        exporter_name,
        exporter_impl,
    ) in _import_config_components(log_exporter_names, "opentelemetry_logs_exporter"):
        if issubclass(exporter_impl, LogRecordExporter):
            log_exporters[exporter_name] = exporter_impl
        else:
            raise RuntimeError(f"{exporter_name} is not a log exporter")

    return trace_exporters, metric_exporters, log_exporters


def _import_sampler_factory(
    sampler_name: str,
) -> Callable[[float | str | None], Sampler]:
    """Load the factory registered for one sampler name.

    The entry point holds a factory rather than a sampler class, because a
    sampler is built from the single argument ``OTEL_TRACES_SAMPLER_ARG``
    carries and each sampler reads that argument differently.

    Args:
        sampler_name: The entry point name in the
            ``opentelemetry_traces_sampler`` group. Surrounding whitespace is
            stripped.

    Returns:
        The factory, which takes the sampler argument and returns a sampler.

    Raises:
        RuntimeError: If the name is not in the group.
    """
    _, sampler_impl = _import_config_components([sampler_name.strip()], _OTEL_SAMPLER_ENTRY_POINT_GROUP)[0]
    return sampler_impl


def _import_sampler(sampler_name: str | None) -> Sampler | None:
    """Build the sampler named by ``OTEL_TRACES_SAMPLER``.

    For ``traceidratio`` and ``parentbased_traceidratio`` the argument is
    parsed as a float; anything that does not parse, including an unset
    variable, is logged at ``WARNING`` level and becomes 1.0, which samples
    every trace. For every other sampler the argument is passed through as a
    string, or as ``None`` when the variable is unset.

    Args:
        sampler_name: The entry point name, or ``None`` or the empty string
            to ask for no sampler.

    Returns:
        The sampler, or ``None`` when none was asked for and when building
        one failed, which leaves the tracer provider on its own default.
        Every failure is logged at ``WARNING`` level and swallowed: an
        unknown name, a factory that raises, and a factory that returns
        something which is not a ``Sampler``.
    """
    if not sampler_name:
        return None
    try:
        sampler_factory = _import_sampler_factory(sampler_name)
        arg = None
        if sampler_name in ("traceidratio", "parentbased_traceidratio"):
            try:
                rate = float(os.getenv(OTEL_TRACES_SAMPLER_ARG, ""))
            except (ValueError, TypeError):
                _logger.warning("Could not convert TRACES_SAMPLER_ARG to float. Using default value 1.0.")
                rate = 1.0
            arg = rate
        else:
            arg = os.getenv(OTEL_TRACES_SAMPLER_ARG)

        sampler = sampler_factory(arg)
        if not isinstance(sampler, Sampler):
            message = f"Sampler factory, {sampler_factory}, produced output, {sampler}, which is not a Sampler."
            _logger.warning(message)
            raise ValueError(message)
        return sampler
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _logger.warning(
            "Using default sampler. Failed to initialize sampler, %s: %s",
            sampler_name,
            exc,
        )
        return None


def _import_id_generator(id_generator_name: str) -> IdGenerator:
    """Build the id generator named by ``OTEL_PYTHON_ID_GENERATOR``.

    Unlike the sampler and the configurators, a failure here is raised rather
    than logged, so a misconfigured id generator stops the SDK from starting.

    Args:
        id_generator_name: The entry point name in the
            ``opentelemetry_id_generator`` group. Surrounding whitespace is
            stripped.

    Returns:
        A new instance, built with no arguments.

    Raises:
        RuntimeError: If the name is not in the group, or if what it loads is
            not an ``IdGenerator`` subclass.
    """
    id_generator_name, id_generator_impl = _import_config_components(
        [id_generator_name.strip()], "opentelemetry_id_generator"
    )[0]

    if issubclass(id_generator_impl, IdGenerator):
        return id_generator_impl()

    raise RuntimeError(f"{id_generator_name} is not an IdGenerator")


def _import_opamp(
    name: Literal["pre_sdk_init_function", "post_sdk_init_function"],
) -> Callable[[Resource], None] | None:
    """Helper for OpAMP entry points loading

    This in development, at the moment we are looking for a callable that takes
    the resource and instantiate an OpAMP agent.
    Since configuration is not specified every implementer may have its own.
    Refer to the opentelemetry-opamp-client package on how to setup the OpAMP agent.

    Args:
        name: Which of the two hooks to load from the
            ``_opentelemetry_opamp`` entry point group.
            ``pre_sdk_init_function`` runs before any provider is built, so it
            can block until a remote configuration arrives.
            ``post_sdk_init_function`` runs once all three providers are
            installed.

    Returns:
        The callable, which takes the resource, or ``None`` when no entry
        point is registered under that name, which is the usual case, and
        when loading one raised ``AttributeError``. The first is logged at
        ``DEBUG`` level and the second at ``WARNING`` level. Any other
        exception from loading the entry point, ``ImportError`` in
        particular, is left to propagate.
    """
    entry_point = None
    try:
        entry_point = next(iter(entry_points(group="_opentelemetry_opamp", name=name)))
        return entry_point.load()
    except StopIteration:
        _logger.debug("No OpAMP init function found")
    except AttributeError as exc:
        _logger.warning(
            "Failed to load OpAMP init function from entry point, %s: %s",
            entry_point,
            exc,
        )

    return None


def _initialize_components(
    auto_instrumentation_version: str | None = None,
    trace_exporter_names: list[str] | None = None,
    metric_exporter_names: list[str] | None = None,
    log_exporter_names: list[str] | None = None,
    sampler: Sampler | None = None,
    resource_attributes: Attributes | None = None,
    id_generator: IdGenerator | None = None,
    setup_logging_handler: bool | None = None,
    exporter_args_map: ExporterArgsMap | None = None,
    span_processors: Sequence[SpanProcessor] | None = None,
    export_span_processor: _ConfigurationExporterSpanProcessorT | None = None,
    log_record_processors: Sequence[LogRecordProcessor] | None = None,
    export_log_record_processor: _ConfigurationExporterLogRecordProcessorT | None = None,
    tracer_configurator: _TracerConfiguratorT | None = None,
    meter_configurator: _MeterConfiguratorT | None = None,
    logger_configurator: _LoggerConfiguratorT | None = None,
):
    """Build and install the tracer, meter and logger providers.

    This is the whole environment-driven startup. Every parameter exists so
    that a distribution can override one decision while leaving the rest to
    the environment: a parameter that is left ``None`` is read from the
    environment instead, and the exporter name lists are added to what the
    environment asks for rather than replacing it.

    The resource is built once and shared by all three providers.

    Args:
        auto_instrumentation_version: The version of the auto instrumentation
            that started the process, recorded as the
            ``telemetry.auto.version`` resource attribute. Pass ``None`` when
            the SDK was started by hand.
        trace_exporter_names: Span exporter entry point names to add to those
            in ``OTEL_TRACES_EXPORTER``.
        metric_exporter_names: Metric exporter entry point names to add to
            those in ``OTEL_METRICS_EXPORTER``.
        log_exporter_names: Log exporter entry point names to add to those in
            ``OTEL_LOGS_EXPORTER``.
        sampler: The sampler to use, or ``None`` to read
            ``OTEL_TRACES_SAMPLER``.
        resource_attributes: Attributes to put on the resource, merged with
            the detected ones and with ``OTEL_RESOURCE_ATTRIBUTES``. The
            mapping is written into, so a caller that reuses it sees
            ``telemetry.auto.version`` appear in it.
        id_generator: The id generator to use, or ``None`` to read
            ``OTEL_PYTHON_ID_GENERATOR``.
        setup_logging_handler: Whether to route the standard library
            ``logging`` through OpenTelemetry, or ``None`` to read
            ``OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED``, which is
            off unless it holds ``true``.
        exporter_args_map: Keyword arguments to construct a given exporter
            class with, keyed by the class. It is shared by all three
            signals.
        span_processors: Span processors to register before the exporting
            ones.
        export_span_processor: What to wrap each span exporter in, or
            ``None`` for ``BatchSpanProcessor``.
        log_record_processors: Log record processors to register before the
            exporting ones.
        export_log_record_processor: What to wrap each log record exporter
            in, or ``None`` for ``BatchLogRecordProcessor``.
        tracer_configurator: Per-scope tracer configuration, or ``None`` to
            read ``OTEL_PYTHON_TRACER_CONFIGURATOR``.
        meter_configurator: Per-scope meter configuration, or ``None`` to
            read ``OTEL_PYTHON_METER_CONFIGURATOR``.
        logger_configurator: Per-scope logger configuration, or ``None`` to
            read ``OTEL_PYTHON_LOGGER_CONFIGURATOR``.

    Raises:
        RuntimeError: If a configured exporter or id generator name cannot be
            resolved. A sampler or a configurator that cannot be resolved is
            logged and skipped instead.
    """
    # pylint: disable=too-many-locals,too-many-branches
    if resource_attributes is None:
        resource_attributes = {}
    # populate version if using auto-instrumentation
    if auto_instrumentation_version:
        resource_attributes[ResourceAttributes.TELEMETRY_AUTO_VERSION] = (  # type: ignore[reportIndexIssue]
            auto_instrumentation_version
        )
    # if env var OTEL_RESOURCE_ATTRIBUTES is given, it will read the service_name
    # from the env variable else defaults to "unknown_service"
    resource = Resource.create(resource_attributes)

    # OpAMP is a system created to configure OpenTelemetry SDKs with a remote config.
    # This is different than other init helpers because setting up OpAMP requires distro
    # provided code as it's not strictly specified. We have two entry points for OpAMP:
    # one called early for people that want it blocking to get an updated config before
    # setting up the rest of the SDK and the other after for people that want the
    # SDK already setup.
    _init_opamp = _import_opamp("pre_sdk_init_function")
    if _init_opamp is not None:
        _init_opamp(resource)

    if trace_exporter_names is None:
        trace_exporter_names = []
    if metric_exporter_names is None:
        metric_exporter_names = []
    if log_exporter_names is None:
        log_exporter_names = []
    span_exporters, metric_exporters, log_exporters = _import_exporters(
        trace_exporter_names + _get_exporter_names("traces"),
        metric_exporter_names + _get_exporter_names("metrics"),
        log_exporter_names + _get_exporter_names("logs"),
    )
    if sampler is None:
        sampler_name = _get_sampler()
        sampler = _import_sampler(sampler_name)
    if id_generator is None:
        id_generator_name = _get_id_generator()
        id_generator = _import_id_generator(id_generator_name)

    if tracer_configurator is None:
        tracer_configurator_name = _get_tracer_configurator()
        tracer_configurator = _import_tracer_configurator(tracer_configurator_name)
    if meter_configurator is None:
        meter_configurator_name = _get_meter_configurator()
        meter_configurator = _import_meter_configurator(meter_configurator_name)
    if logger_configurator is None:
        logger_configurator_name = _get_logger_configurator()
        logger_configurator = _import_logger_configurator(logger_configurator_name)

    _init_tracing(
        exporters=span_exporters,
        id_generator=id_generator,
        sampler=sampler,
        resource=resource,
        exporter_args_map=exporter_args_map,
        span_processors=span_processors,
        export_span_processor=export_span_processor,
        tracer_configurator=tracer_configurator,
    )
    _init_metrics(
        exporters_or_readers=metric_exporters,
        resource=resource,
        exporter_args_map=exporter_args_map,
        meter_configurator=meter_configurator,
    )
    if setup_logging_handler is None:
        setup_logging_handler = (
            os.getenv(_OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED, "false").strip().lower() == "true"
        )
    _init_logging(
        log_exporters,
        resource,
        setup_logging_handler,
        exporter_args_map=exporter_args_map,
        log_record_processors=log_record_processors,
        export_log_record_processor=export_log_record_processor,
        logger_configurator=logger_configurator,
    )

    _init_opamp = _import_opamp("post_sdk_init_function")
    if _init_opamp is not None:
        _init_opamp(resource)


class _BaseConfigurator(ABC):
    """An ABC for configurators

    Configurators are used to configure
    SDKs (i.e. TracerProvider, MeterProvider, Processors...)
    to reduce the amount of manual configuration required.
    """

    _instance = None
    _is_instrumented = False

    def __new__(cls, *args, **kwargs):
        """Return the one instance of ``cls``, creating it on the first call.

        The instance is cached as the ``_instance`` attribute of the class it
        was first built for, and that attribute is looked up through the
        inheritance chain, so a subclass of a class that has already been
        instantiated receives that class's instance rather than one of its
        own. Arguments are accepted and ignored, which means a second
        construction with different arguments silently returns the first
        instance.

        Args:
            *args: Ignored.
            **kwargs: Ignored.

        Returns:
            The single instance of ``cls``.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    @abstractmethod
    def _configure(self, **kwargs):
        """Configure the SDK

        This is what a subclass implements. ``configure`` is its only
        caller, and it holds no guard, so calling ``configure`` twice runs
        this twice.

        Args:
            **kwargs: Whatever the caller of ``configure`` passed. The
                meaning is up to the implementation;
                ``_OTelSDKConfigurator`` forwards them to
                ``_initialize_components``.
        """

    def configure(self, **kwargs):
        """Configure the SDK

        Args:
            **kwargs: Forwarded unchanged to ``_configure``.
        """
        self._configure(**kwargs)


class _OTelSDKConfigurator(_BaseConfigurator):
    """A basic Configurator by OTel Python for initializing OTel SDK components

    Initializes several crucial OTel SDK components (i.e. TracerProvider,
    MeterProvider, Processors...) according to a default implementation. Other
    Configurators can subclass and slightly alter this initialization.

    NOTE: This class should not be instantiated nor should it become an entry
    point on the `opentelemetry-sdk` package. Instead, distros should subclass
    this Configurator and enhance it as needed.
    """

    def _configure(self, **kwargs):
        """Start the SDK, from a configuration file when one is named.

        Setting ``OTEL_CONFIG_FILE`` switches to declarative configuration,
        which reads the whole SDK out of that file instead of out of the
        environment variables this module otherwise consults. The file is
        not sealed off from the environment: the loader resolves a
        ``${VAR}`` reference in any value it reads, so a configured value
        may still come from an environment variable. The file is handled by
        the separate
        ``opentelemetry-configuration`` distribution, imported only on this
        path so that the SDK does not depend on it at runtime. Any ``kwargs``
        are then ignored, with a warning naming them, since the file is the
        only source.

        Args:
            **kwargs: Forwarded to ``_initialize_components`` when no
                configuration file is set, and ignored when one is.

        Raises:
            RuntimeError: If ``OTEL_CONFIG_FILE`` is set and
                ``opentelemetry-configuration`` is not installed.
        """
        if config_file := environ.get(OTEL_CONFIG_FILE):
            # Declarative configuration lives in the separate
            # ``opentelemetry-configuration`` package. Import lazily so the
            # SDK has no runtime dependency on it; users who don't set
            # ``OTEL_CONFIG_FILE`` never pay the import cost.
            try:
                # opentelemetry-configuration is an optional runtime dep
                # and is not installed in this package's lint env, so
                # silence the static-analysis no-name-in-module on the
                # conditional import.
                # pylint: disable=import-outside-toplevel,no-name-in-module
                from opentelemetry.configuration import (  # noqa: PLC0415
                    configure_sdk,
                    load_config_file,
                )
            except ImportError as exc:
                raise RuntimeError(
                    f"{OTEL_CONFIG_FILE} is set but "
                    "opentelemetry-configuration is not installed. "
                    "Install it with: pip install opentelemetry-configuration"
                ) from exc

            if kwargs:
                _logger.warning(
                    "%s is set; ignoring configurator kwargs: %s",
                    OTEL_CONFIG_FILE,
                    sorted(kwargs),
                )
            configure_sdk(load_config_file(config_file))
            return
        _initialize_components(**kwargs)
