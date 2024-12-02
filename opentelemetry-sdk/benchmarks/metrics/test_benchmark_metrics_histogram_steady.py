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

# pylint: disable=invalid-name
import itertools

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    View,
)

MAX_BOUND_VALUE = 10000


def _generate_bounds(bound_count):
    bounds = []
    for i in range(bound_count):
        bounds.append(i * MAX_BOUND_VALUE / bound_count)
    return bounds


hist_view_10 = View(
    instrument_name="test_histogram_10_bound",
    aggregation=ExplicitBucketHistogramAggregation(_generate_bounds(10)),
)
hist_view_49 = View(
    instrument_name="test_histogram_49_bound",
    aggregation=ExplicitBucketHistogramAggregation(_generate_bounds(49)),
)
hist_view_50 = View(
    instrument_name="test_histogram_50_bound",
    aggregation=ExplicitBucketHistogramAggregation(_generate_bounds(50)),
)
hist_view_1000 = View(
    instrument_name="test_histogram_1000_bound",
    aggregation=ExplicitBucketHistogramAggregation(_generate_bounds(1000)),
)
reader = InMemoryMetricReader()
provider = MeterProvider(
    metric_readers=[reader],
    views=[
        hist_view_10,
        hist_view_49,
        hist_view_50,
        hist_view_1000,
    ],
)
meter = provider.get_meter("sdk_meter_provider")
hist = meter.create_histogram("test_histogram_default")
hist10 = meter.create_histogram("test_histogram_10_bound")
hist49 = meter.create_histogram("test_histogram_49_bound")
hist50 = meter.create_histogram("test_histogram_50_bound")
hist1000 = meter.create_histogram("test_histogram_1000_bound")


def test_histogram_record(benchmark):
    values = itertools.cycle(_generate_bounds(10))

    def benchmark_histogram_record():
        hist.record(next(values))

    benchmark(benchmark_histogram_record)


def test_histogram_record_10(benchmark):
    values = itertools.cycle(_generate_bounds(10))

    def benchmark_histogram_record_10():
        hist10.record(next(values))

    benchmark(benchmark_histogram_record_10)


def test_histogram_record_49(benchmark):
    values = itertools.cycle(_generate_bounds(49))

    def benchmark_histogram_record_49():
        hist49.record(next(values))

    benchmark(benchmark_histogram_record_49)


def test_histogram_record_50(benchmark):
    values = itertools.cycle(_generate_bounds(50))

    def benchmark_histogram_record_50():
        hist50.record(next(values))

    benchmark(benchmark_histogram_record_50)


def test_histogram_record_1000(benchmark):
    values = itertools.cycle(_generate_bounds(1000))

    def benchmark_histogram_record_1000():
        hist1000.record(next(values))

    benchmark(benchmark_histogram_record_1000)
