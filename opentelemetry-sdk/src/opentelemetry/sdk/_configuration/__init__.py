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
#

"""
OpenTelemetry SDK Configurator for Easy Instrumentation with Distros
"""

import logging
import os
from abc import ABC, abstractmethod
from os import environ
from typing import Dict, Optional, Sequence, Tuple, Type

from pkg_resources import iter_entry_points

from opentelemetry.environment_variables import (
    OTEL_LOGS_EXPORTER,
    OTEL_METRICS_EXPORTER,
    OTEL_PYTHON_ID_GENERATOR,
    OTEL_TRACES_EXPORTER,
)
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk._logs import (
    LogEmitterProvider,
    LoggingHandler,
    set_log_emitter_provider,
)
from opentelemetry.sdk._logs.export import BatchLogProcessor, LogExporter
from opentelemetry.sdk.environment_variables import (
    _OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.id_generator import IdGenerator
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import set_tracer_provider

_EXPORTER_OTLP = "otlp"
_EXPORTER_OTLP_PROTO_GRPC = "otlp_proto_grpc"

_RANDOM_ID_GENERATOR = "random"
_DEFAULT_ID_GENERATOR = _RANDOM_ID_GENERATOR


def _get_id_generator() -> str:
    return environ.get(OTEL_PYTHON_ID_GENERATOR, _DEFAULT_ID_GENERATOR)


def _get_exporter_names(names: str) -> Sequence[str]:
    exporters = set()

    if names and names.lower().strip() != "none":
        exporters.update({_exporter.strip() for _exporter in names.split(",")})

    if _EXPORTER_OTLP in exporters:
        exporters.remove(_EXPORTER_OTLP)
        exporters.add(_EXPORTER_OTLP_PROTO_GRPC)

    return list(exporters)


def _init_tracing(
    exporters: Dict[str, Type[SpanExporter]],
    id_generator: IdGenerator,
    auto_instrumentation_version: Optional[str] = None,
):
    # if env var OTEL_RESOURCE_ATTRIBUTES is given, it will read the service_name
    # from the env variable else defaults to "unknown_service"
    auto_resource = {}
    # populate version if using auto-instrumentation
    if auto_instrumentation_version:
        auto_resource[
            ResourceAttributes.TELEMETRY_AUTO_VERSION
        ] = auto_instrumentation_version
    provider = TracerProvider(
        id_generator=id_generator(),
        resource=Resource.create(auto_resource),
    )
    set_tracer_provider(provider)

    for _, exporter_class in exporters.items():
        exporter_args = {}
        provider.add_span_processor(
            BatchSpanProcessor(exporter_class(**exporter_args))
        )


def _init_metrics(
    exporters: Dict[str, Type[MetricExporter]],
    auto_instrumentation_version: Optional[str] = None,
):
    # if env var OTEL_RESOURCE_ATTRIBUTES is given, it will read the service_name
    # from the env variable else defaults to "unknown_service"
    auto_resource = {}
    # populate version if using auto-instrumentation
    if auto_instrumentation_version:
        auto_resource[
            ResourceAttributes.TELEMETRY_AUTO_VERSION
        ] = auto_instrumentation_version

    metric_readers = []

    for _, exporter_class in exporters.items():
        exporter_args = {}
        metric_readers.append(
            PeriodicExportingMetricReader(exporter_class(**exporter_args))
        )

    provider = MeterProvider(
        resource=Resource.create(auto_resource), metric_readers=metric_readers
    )
    set_meter_provider(provider)


def _init_logging(
    exporters: Dict[str, Type[LogExporter]],
    auto_instrumentation_version: Optional[str] = None,
):
    # if env var OTEL_RESOURCE_ATTRIBUTES is given, it will read the service_name
    # from the env variable else defaults to "unknown_service"
    auto_resource = {}
    # populate version if using auto-instrumentation
    if auto_instrumentation_version:
        auto_resource[
            ResourceAttributes.TELEMETRY_AUTO_VERSION
        ] = auto_instrumentation_version
    provider = LogEmitterProvider(resource=Resource.create(auto_resource))
    set_log_emitter_provider(provider)

    for _, exporter_class in exporters.items():
        exporter_args = {}
        provider.add_log_processor(
            BatchLogProcessor(exporter_class(**exporter_args))
        )

    log_emitter = provider.get_log_emitter(__name__)
    handler = LoggingHandler(level=logging.NOTSET, log_emitter=log_emitter)

    logging.getLogger().addHandler(handler)


def _import_config_components(
    selected_components, entry_point_name
) -> Sequence[Tuple[str, object]]:
    component_entry_points = {
        ep.name: ep for ep in iter_entry_points(entry_point_name)
    }
    component_impls = []
    for selected_component in selected_components:
        entry_point = component_entry_points.get(selected_component, None)
        if not entry_point:
            raise RuntimeError(
                f"Requested component '{selected_component}' not found in entry points for '{entry_point_name}'"
            )

        component_impl = entry_point.load()
        component_impls.append((selected_component, component_impl))

    return component_impls


def _import_exporters(
    trace_exporter_names: Sequence[str],
    metric_exporter_names: Sequence[str],
    log_exporter_names: Sequence[str],
) -> Tuple[
    Dict[str, Type[SpanExporter]],
    Dict[str, Type[MetricExporter]],
    Dict[str, Type[LogExporter]],
]:
    trace_exporters = {}
    metric_exporters = {}
    log_exporters = {}

    for (exporter_name, exporter_impl,) in _import_config_components(
        trace_exporter_names, "opentelemetry_traces_exporter"
    ):
        if issubclass(exporter_impl, SpanExporter):
            trace_exporters[exporter_name] = exporter_impl
        else:
            raise RuntimeError(f"{exporter_name} is not a trace exporter")

    for (exporter_name, exporter_impl,) in _import_config_components(
        metric_exporter_names, "opentelemetry_metrics_exporter"
    ):
        if issubclass(exporter_impl, MetricExporter):
            metric_exporters[exporter_name] = exporter_impl
        else:
            raise RuntimeError(f"{exporter_name} is not a metric exporter")

    for (exporter_name, exporter_impl,) in _import_config_components(
        log_exporter_names, "opentelemetry_logs_exporter"
    ):
        if issubclass(exporter_impl, LogExporter):
            log_exporters[exporter_name] = exporter_impl
        else:
            raise RuntimeError(f"{exporter_name} is not a log exporter")

    return trace_exporters, metric_exporters, log_exporters


def _import_id_generator(id_generator_name: str) -> IdGenerator:
    # pylint: disable=unbalanced-tuple-unpacking
    [(id_generator_name, id_generator_impl)] = _import_config_components(
        [id_generator_name.strip()], "opentelemetry_id_generator"
    )

    if issubclass(id_generator_impl, IdGenerator):
        return id_generator_impl

    raise RuntimeError(f"{id_generator_name} is not an IdGenerator")


def _initialize_components(auto_instrumentation_version):
    trace_exporters, metric_exporters, log_exporters = _import_exporters(
        _get_exporter_names(environ.get(OTEL_TRACES_EXPORTER)),
        _get_exporter_names(environ.get(OTEL_METRICS_EXPORTER)),
        _get_exporter_names(environ.get(OTEL_LOGS_EXPORTER)),
    )
    id_generator_name = _get_id_generator()
    id_generator = _import_id_generator(id_generator_name)
    _init_tracing(trace_exporters, id_generator, auto_instrumentation_version)
    _init_metrics(metric_exporters, auto_instrumentation_version)
    logging_enabled = os.getenv(
        _OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED, "false"
    )
    if logging_enabled.strip().lower() == "true":
        _init_logging(log_exporters, auto_instrumentation_version)


class _BaseConfigurator(ABC):
    """An ABC for configurators

    Configurators are used to configure
    SDKs (i.e. TracerProvider, MeterProvider, Processors...)
    to reduce the amount of manual configuration required.
    """

    _instance = None
    _is_instrumented = False

    def __new__(cls, *args, **kwargs):

        if cls._instance is None:
            cls._instance = object.__new__(cls, *args, **kwargs)

        return cls._instance

    @abstractmethod
    def _configure(self, **kwargs):
        """Configure the SDK"""

    def configure(self, **kwargs):
        """Configure the SDK"""
        self._configure(**kwargs)


class _OTelSDKConfigurator(_BaseConfigurator):
    """A basic Configurator by OTel Python for initalizing OTel SDK components

    Initializes several crucial OTel SDK components (i.e. TracerProvider,
    MeterProvider, Processors...) according to a default implementation. Other
    Configurators can subclass and slightly alter this initialization.

    NOTE: This class should not be instantiated nor should it become an entry
    point on the `opentelemetry-sdk` package. Instead, distros should subclass
    this Configurator and enchance it as needed.
    """

    def _configure(self, **kwargs):
        _initialize_components(kwargs.get("auto_instrumentation_version"))
