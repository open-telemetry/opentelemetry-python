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

import opentelemetry.sdk.trace as trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import sampling

tracer = trace.TracerProvider(
    sampler=sampling.DEFAULT_ON,
    resource=Resource(
        {
            "service.name": "A123456789",
            "service.version": "1.34567890",
            "service.instance.id": "123ab456-a123-12ab-12ab-12340a1abc12",
        }
    ),
).get_tracer("sdk_tracer_provider")


def test_simple_start_span(benchmark):
    def benchmark_start_as_current_span():
        span = tracer.start_span(
            "benchmarkedSpan",
            attributes={"long.attribute": -10000000001000000000},
        )
        span.add_event("benchmarkEvent")
        span.end()

    benchmark(benchmark_start_as_current_span)


def test_simple_start_as_current_span(benchmark):
    def benchmark_start_as_current_span():
        with tracer.start_as_current_span(
            "benchmarkedSpan",
            attributes={"long.attribute": -10000000001000000000},
        ) as span:
            span.add_event("benchmarkEvent")

    benchmark(benchmark_start_as_current_span)
