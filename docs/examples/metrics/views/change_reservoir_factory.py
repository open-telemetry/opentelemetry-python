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

import random
import time
from typing import Any, Callable, Optional, Sequence, Set, Type

from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics._internal.aggregation import (
    Aggregation,
    DefaultAggregation,
    _Aggregation,
    _ExplicitBucketHistogramAggregation,
    _ExponentialBucketHistogramAggregation,
)
from opentelemetry.sdk.metrics._internal.exemplar import (
    AlignedHistogramBucketExemplarReservoir,
    ExemplarReservoir,
    ExemplarReservoirFactory,
    SimpleFixedSizeExemplarReservoir,
)
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import View


# Returns a factory for creating an exemplar reservoir based on the aggregation type and specified parameters
def generalized_reservoir_factory(
    size: int = 1, boundaries: Sequence[float] = None
) -> Callable[[Type[_Aggregation]], ExemplarReservoirFactory]:
    def factory(
        aggregationType: Type[_Aggregation],
    ) -> ExemplarReservoirFactory:
        if issubclass(aggregationType, _ExplicitBucketHistogramAggregation):
            return lambda **kwargs: AlignedHistogramBucketExemplarReservoir(
                boundaries=boundaries or [],
                **{k: v for k, v in kwargs.items() if k != "boundaries"},
            )
        else:
            return lambda **kwargs: SimpleFixedSizeExemplarReservoir(
                size=size, **kwargs
            )

    return factory


# Create a custom reservoir factory with specified parameters
custom_reservoir_factory = generalized_reservoir_factory(size=10)

# Create a view with the custom reservoir factory
change_reservoir_factory_view = View(
    instrument_name="my.counter",
    name="name",
    aggregation=DefaultAggregation(),
    exemplar_reservoir_factory=custom_reservoir_factory,
)

# Use console exporter for the example
exporter = ConsoleMetricExporter()

# Create a metric reader with stdout exporter
reader = PeriodicExportingMetricReader(exporter, export_interval_millis=1_000)
provider = MeterProvider(
    metric_readers=[
        reader,
    ],
    views=[
        change_reservoir_factory_view,
    ],
)
set_meter_provider(provider)

meter = get_meter_provider().get_meter("reservoir-factory-change", "0.1.2")

my_counter = meter.create_counter("my.counter")

while 1:
    my_counter.add(random.randint(1, 10))
    time.sleep(random.random())
