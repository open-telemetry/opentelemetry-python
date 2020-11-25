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

from logging import getLogger
from typing import Sequence, Tuple

from pkg_resources import iter_entry_points

from opentelemetry import trace
from opentelemetry.configuration import Configuration
from opentelemetry.sdk.metrics.export import MetricsExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchExportSpanProcessor,
    SpanExporter,
)

logger = getLogger(__file__)

EXPORTER_OTLP = "otlp"
EXPORTER_OTLP_SPAN = "otlp_span"
EXPORTER_OTLP_METRIC = "otlp_metric"
_DEFAULT_EXPORTER = EXPORTER_OTLP

RANDOM_IDS_GENERATOR = "random"
_DEFAULT_IDS_GENERATOR = RANDOM_IDS_GENERATOR


def get_ids_generator() -> str:
    return Configuration().IDS_GENERATOR or _DEFAULT_IDS_GENERATOR


def get_service_name() -> str:
    return Configuration().SERVICE_NAME or ""


def get_exporter_names() -> Sequence[str]:
    exporter = Configuration().EXPORTER or _DEFAULT_EXPORTER
    if exporter.lower().strip() == "none":
        return []

    names = []
    for exp in exporter.split(","):
        name = exp.strip()
        if name == EXPORTER_OTLP:
            names.append(EXPORTER_OTLP_SPAN)
            names.append(EXPORTER_OTLP_METRIC)
        else:
            names.append(name)
    return names


def init_tracing(
    exporters: Sequence[SpanExporter], ids_generator: trace.IdsGenerator
):
    service_name = get_service_name()
    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name}),
        ids_generator=ids_generator(),
    )
    trace.set_tracer_provider(provider)

    for exporter_name, exporter_class in exporters.items():
        exporter_args = {}
        if exporter_name not in [
            EXPORTER_OTLP,
            EXPORTER_OTLP_SPAN,
        ]:
            exporter_args["service_name"] = service_name

        provider.add_span_processor(
            BatchExportSpanProcessor(exporter_class(**exporter_args))
        )


def init_metrics(exporters: Sequence[MetricsExporter]):
    if exporters:
        logger.warning("automatic metric initialization is not supported yet.")


def import_tracer_provider_config_components(
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


def import_exporters(
    exporter_names: Sequence[str],
) -> Tuple[Sequence[SpanExporter], Sequence[MetricsExporter]]:
    trace_exporters, metric_exporters = {}, {}

    for (
        exporter_name,
        exporter_impl,
    ) in import_tracer_provider_config_components(
        exporter_names, "opentelemetry_exporter"
    ):
        if issubclass(exporter_impl, SpanExporter):
            trace_exporters[exporter_name] = exporter_impl
        elif issubclass(exporter_impl, MetricsExporter):
            metric_exporters[exporter_name] = exporter_impl
        else:
            raise RuntimeError(
                "{0} is neither a trace exporter nor a metric exporter".format(
                    exporter_name
                )
            )
    return trace_exporters, metric_exporters


def import_ids_generator(ids_generator_name: str) -> trace.IdsGenerator:
    # pylint: disable=unbalanced-tuple-unpacking
    [
        (ids_generator_name, ids_generator_impl)
    ] = import_tracer_provider_config_components(
        [ids_generator_name.strip()], "opentelemetry_ids_generator"
    )

    if issubclass(ids_generator_impl, trace.IdsGenerator):
        return ids_generator_impl

    raise RuntimeError("{0} is not an IdsGenerator".format(ids_generator_name))


def initialize_components():
    exporter_names = get_exporter_names()
    trace_exporters, metric_exporters = import_exporters(exporter_names)
    ids_generator_name = get_ids_generator()
    ids_generator = import_ids_generator(ids_generator_name)
    init_tracing(trace_exporters, ids_generator)

    # We don't support automatic initialization for metric yet but have added
    # some boilerplate in order to make sure current implementation does not
    # lock us out of supporting metrics later without major surgery.
    init_metrics(metric_exporters)
