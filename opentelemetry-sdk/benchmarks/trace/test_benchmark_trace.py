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

from functools import lru_cache

import pytest

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import (
    TracerProvider,
    _default_tracer_configurator,
    _RuleBasedTracerConfigurator,
    _tracer_name_matches_glob,
    _TracerConfig,
    sampling,
)

tracer = TracerProvider(
    sampler=sampling.DEFAULT_ON,
    resource=Resource(
        {
            "service.name": "A123456789",
            "service.version": "1.34567890",
            "service.instance.id": "123ab456-a123-12ab-12ab-12340a1abc12",
        }
    ),
).get_tracer("sdk_tracer_provider")


@pytest.fixture(params=[None, 0, 1, 10, 50])
def num_tracer_configurator_rules(request):
    return request.param


def test_simple_start_span(benchmark):
    def benchmark_start_span():
        span = tracer.start_span(
            "benchmarkedSpan",
            attributes={"long.attribute": -10000000001000000000},
        )
        span.add_event("benchmarkEvent")
        span.end()

    benchmark(benchmark_start_span)


# pylint: disable=protected-access,redefined-outer-name
def test_simple_start_span_with_tracer_configurator_rules(
    benchmark, num_tracer_configurator_rules
):
    def benchmark_start_span():
        span = tracer.start_span(
            "benchmarkedSpan",
            attributes={"long.attribute": -10000000001000000000},
        )
        span.add_event("benchmarkEvent")
        span.end()

    @lru_cache
    def tracer_configurator(tracer_scope):
        # this is testing 100 rules that is an extreme case
        return _RuleBasedTracerConfigurator(
            rules=[
                (
                    _tracer_name_matches_glob(glob_pattern=str(i)),
                    _TracerConfig(is_enabled=True),
                )
                for i in range(num_tracer_configurator_rules)
            ],
            default_config=_TracerConfig(is_enabled=True),
        )(tracer_scope=tracer_scope)

    tracer_provider = tracer._tracer_provider
    tracer_provider._set_tracer_configurator(
        tracer_configurator=tracer_configurator
    )
    if num_tracer_configurator_rules is None:
        tracer._tracer_provider = None
    benchmark(benchmark_start_span)
    tracer_provider._set_tracer_configurator(
        tracer_configurator=_default_tracer_configurator
    )
    if num_tracer_configurator_rules is None:
        tracer._tracer_provider = tracer_provider


def test_simple_start_as_current_span(benchmark):
    def benchmark_start_as_current_span():
        with tracer.start_as_current_span(
            "benchmarkedSpan",
            attributes={"long.attribute": -10000000001000000000},
        ) as span:
            span.add_event("benchmarkEvent")

    benchmark(benchmark_start_as_current_span)
