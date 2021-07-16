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

from os import environ
from typing import Sequence, Tuple

from pkg_resources import iter_entry_points

from opentelemetry import trace
from opentelemetry.environment_variables import (
    OTEL_PYTHON_ID_GENERATOR,
    OTEL_TRACES_EXPORTER,
)
from opentelemetry.instrumentation.configurator import BaseConfigurator
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.id_generator import IdGenerator

_EXPORTER_OTLP = "otlp"
_EXPORTER_OTLP_SPAN = "otlp_proto_grpc_span"

_RANDOM_ID_GENERATOR = "random"
_DEFAULT_ID_GENERATOR = _RANDOM_ID_GENERATOR


def _get_id_generator() -> str:
    return environ.get(OTEL_PYTHON_ID_GENERATOR, _DEFAULT_ID_GENERATOR)


def _get_exporter_names() -> Sequence[str]:
    trace_exporters = environ.get(OTEL_TRACES_EXPORTER)

    exporters = set()

    if trace_exporters and trace_exporters.lower().strip() != "none":
        exporters.update(
            {
                trace_exporter.strip()
                for trace_exporter in trace_exporters.split(",")
            }
        )

    if _EXPORTER_OTLP in exporters:
        exporters.remove(_EXPORTER_OTLP)
        exporters.add(_EXPORTER_OTLP_SPAN)

    return list(exporters)


def _init_tracing(
    exporters: Sequence[SpanExporter], id_generator: IdGenerator
):
    # if env var OTEL_RESOURCE_ATTRIBUTES is given, it will read the service_name
    # from the env variable else defaults to "unknown_service"
    provider = TracerProvider(
        id_generator=id_generator(),
    )
    trace.set_tracer_provider(provider)

    for _, exporter_class in exporters.items():
        exporter_args = {}
        provider.add_span_processor(
            BatchSpanProcessor(exporter_class(**exporter_args))
        )


def _import_tracer_provider_config_components(
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
                "Requested component '{}' not found in entry points for '{}'".format(
                    selected_component, entry_point_name
                )
            )

        component_impl = entry_point.load()
        component_impls.append((selected_component, component_impl))

    return component_impls


def _import_exporters(
    exporter_names: Sequence[str],
) -> Sequence[SpanExporter]:
    trace_exporters = {}

    for (
        exporter_name,
        exporter_impl,
    ) in _import_tracer_provider_config_components(
        exporter_names, "opentelemetry_exporter"
    ):
        if issubclass(exporter_impl, SpanExporter):
            trace_exporters[exporter_name] = exporter_impl
        else:
            raise RuntimeError(
                "{0} is not a trace exporter".format(exporter_name)
            )
    return trace_exporters


def _import_id_generator(id_generator_name: str) -> IdGenerator:
    # pylint: disable=unbalanced-tuple-unpacking
    [
        (id_generator_name, id_generator_impl)
    ] = _import_tracer_provider_config_components(
        [id_generator_name.strip()], "opentelemetry_id_generator"
    )

    if issubclass(id_generator_impl, IdGenerator):
        return id_generator_impl

    raise RuntimeError("{0} is not an IdGenerator".format(id_generator_name))


def _initialize_components():
    exporter_names = _get_exporter_names()
    trace_exporters = _import_exporters(exporter_names)
    id_generator_name = _get_id_generator()
    id_generator = _import_id_generator(id_generator_name)
    _init_tracing(trace_exporters, id_generator)


class _OTelSDKConfigurator(BaseConfigurator):
    """A basic Configurator by OTel Python for initalizing OTel SDK components

    Initializes several crucial OTel SDK components (i.e. TracerProvider,
    MeterProvider, Processors...) according to a default implementation. Other
    Configurators can subclass and slightly alter this initialization.

    NOTE: This class should not be instantiated nor should it become an entry
    point on the `opentelemetry-sdk` package. Instead, distros should subclass
    this Configurator and enchance it as needed.
    """

    def _configure(self, **kwargs):
        _initialize_components()
