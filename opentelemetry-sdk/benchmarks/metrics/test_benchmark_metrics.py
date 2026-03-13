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
from opentelemetry.sdk.metrics._internal import (
    _default_meter_configurator,
    _disable_meter_configurator,
    _MeterConfig,
    _RuleBasedMeterConfigurator,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    InMemoryMetricReader,
)
from opentelemetry.sdk.util.instrumentation import _scope_name_matches_glob

reader_cumulative = InMemoryMetricReader()
reader_delta = InMemoryMetricReader(
    preferred_temporality={
        Counter: AggregationTemporality.DELTA,
    },
)
provider_reader_cumulative = MeterProvider(
    metric_readers=[reader_cumulative],
)
provider_reader_delta = MeterProvider(metric_readers=[reader_delta])
meter_cumulative = provider_reader_cumulative.get_meter("sdk_meter_provider")
meter_delta = provider_reader_delta.get_meter("sdk_meter_provider_delta")
counter_cumulative = meter_cumulative.create_counter("test_counter")
counter_delta = meter_delta.create_counter("test_counter2")
udcounter = meter_cumulative.create_up_down_counter("test_udcounter")


@pytest.mark.parametrize(
    ("num_labels", "temporality"),
    [
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
    ],
)
def test_counter_add(benchmark, num_labels, temporality):
    labels = {}
    # pylint: disable=invalid-name
    for i in range(num_labels):
        labels = {f"Key{i}": f"Value{i}" for i in range(num_labels)}

    def benchmark_counter_add():
        if temporality == "cumulative":
            counter_cumulative.add(1, labels)
        else:
            counter_delta.add(1, labels)

    benchmark(benchmark_counter_add)


@pytest.mark.parametrize("num_labels", [0, 1, 3, 5, 10])
def test_up_down_counter_add(benchmark, num_labels):
    labels = {}
    # pylint: disable=invalid-name
    for i in range(num_labels):
        labels = {f"Key{i}": f"Value{i}" for i in range(num_labels)}

    def benchmark_up_down_counter_add():
        udcounter.add(1, labels)

    benchmark(benchmark_up_down_counter_add)


@pytest.fixture(params=[None, 0, 1, 10, 50])
def num_meter_configurator_rules(request):
    return request.param


# pylint: disable=protected-access,redefined-outer-name
def test_counter_add_with_meter_configurator_rules(
    benchmark, num_meter_configurator_rules
):
    def benchmark_counter_add():
        counter_cumulative.add(1, {})

    if num_meter_configurator_rules is None:
        # None case: meter is disabled, measuring the short-circuit path
        provider_reader_cumulative._set_meter_configurator(
            meter_configurator=_disable_meter_configurator
        )
    else:

        def meter_configurator(meter_scope):
            return _RuleBasedMeterConfigurator(
                rules=[
                    (
                        _scope_name_matches_glob(glob_pattern=str(i)),
                        _MeterConfig(is_enabled=True),
                    )
                    for i in range(num_meter_configurator_rules)
                ],
                default_config=_MeterConfig(is_enabled=True),
            )(meter_scope)

        provider_reader_cumulative._set_meter_configurator(
            meter_configurator=meter_configurator
        )

    benchmark(benchmark_counter_add)
    provider_reader_cumulative._set_meter_configurator(
        meter_configurator=_default_meter_configurator
    )
