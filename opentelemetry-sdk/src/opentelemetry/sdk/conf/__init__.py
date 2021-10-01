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
OpenTelemetry SDK configuration helpers
"""

from typing import Any, Callable, Optional, Sequence, Union, cast

from typing_extensions import Protocol

from opentelemetry import trace
from opentelemetry.sdk._configuration import (
    _import_exporters_from_env,
    _import_id_generator_from_env,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import (
    ConcurrentMultiSpanProcessor,
    SpanLimits,
    SpanProcessor,
    SynchronousMultiSpanProcessor,
    TracerProvider,
)
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
)
from opentelemetry.sdk.trace.id_generator import IdGenerator
from opentelemetry.sdk.trace.sampling import Sampler


class TracerProviderFactory(Protocol):
    def __call__(
        self,
        sampler: Optional[Sampler],
        resource: Optional[Resource],
        shutdown_on_exit: Optional[bool],
        active_span_processor: Optional[
            Union[SynchronousMultiSpanProcessor, ConcurrentMultiSpanProcessor]
        ],
        id_generator: Optional[IdGenerator],
        span_limits: Optional[SpanLimits],
        *args: Sequence[Any],
        **kwargs: Sequence[Any],
    ) -> TracerProvider:
        pass


class SpanProcessorFactory(Protocol):
    def __call__(
        self,
        exporter: SpanExporter,
        *args: Sequence[Any],
        **kwargs: Sequence[Any],
    ) -> SpanProcessor:
        pass


SpanExporterFactory = Callable[..., SpanExporter]


def configure_tracing(
    provider_factory: Callable[..., TracerProvider] = TracerProvider,
    processor_factories: Sequence[SpanProcessorFactory] = None,
    exporter_factories: Sequence[SpanExporterFactory] = None,
    set_global: bool = True,
) -> TracerProvider:
    """configure_tracing is a convenience function used to quickly setup an OpenTelemetry SDK tracing pipeline."""

    # default factories
    processor_factories = processor_factories or [BatchSpanProcessor]
    env_exporters = cast(
        Sequence[SpanExporterFactory], _import_exporters_from_env()
    )
    exporter_factories = (
        exporter_factories or env_exporters or [ConsoleSpanExporter]
    )

    id_generator = _import_id_generator_from_env()
    provider = provider_factory(id_generator=id_generator)

    # for each exporter, create a SpanProcessor and add it to the provider
    for exporter_factory in exporter_factories:
        for processor_factory in processor_factories:
            processor = processor_factory(exporter_factory())
            provider.add_span_processor(processor)

    # set as the global tracer provider if requested
    if set_global:
        trace.set_tracer_provider(provider)

    return provider
