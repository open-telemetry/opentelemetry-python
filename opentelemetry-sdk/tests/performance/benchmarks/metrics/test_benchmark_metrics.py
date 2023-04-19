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
import pytest

from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import AggregationTemporality, InMemoryMetricReader

reader = InMemoryMetricReader()
reader_delta = InMemoryMetricReader(
    preferred_temporality = {
        Counter: AggregationTemporality.DELTA,
    },
)
provider = MeterProvider(metric_readers=[reader], )
provider2 = MeterProvider(metric_readers=[reader_delta])
meter = provider.get_meter("sdk_meter_provider")
meter2 = provider2.get_meter("sdk_meter_provider_delta")
counter = meter.create_counter("test_counter")
counter2 = meter2.create_counter("test_counter2")
udcounter = meter.create_up_down_counter("test_udcounter")


@pytest.mark.parametrize(("num_labels", "temporality"), [
    (0, "delta"),
    (1, "delta"),
    (3, "delta"),
    (5, "delta"),
    (10, "delta"),
    (0, "cumulative"),
    (1, "cumulative"),
    (3, "cumulative"),
    (5, "cumulative"),
    (10, "cumulative"),
])
def test_counter_add(benchmark, num_labels, temporality):
    labels = {}
    for i in range(num_labels):
        labels["Key{}".format(i)] = "Value{}".format(i)
    def benchmark_counter_add():
        if temporality == "cumulative":
            counter.add(1, labels)
        else:
            counter2.add(1, labels)

    benchmark(benchmark_counter_add)


@pytest.mark.parametrize("num_labels", [0, 1, 3, 5, 10])
def test_up_down_counter_add(benchmark, num_labels):
    labels = {}
    for i in range(num_labels):
        labels["Key{}".format(i)] = "Value{}".format(i)
    def benchmark_up_down_counter_add():
        udcounter.add(1, labels)

    benchmark(benchmark_up_down_counter_add)
