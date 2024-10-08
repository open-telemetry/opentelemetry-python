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
from typing import Type

from opentelemetry import trace
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.aggregation import (
    DefaultAggregation,
    _Aggregation,
    _ExplicitBucketHistogramAggregation,
)
from opentelemetry.sdk.metrics._internal.exemplar import (
    AlignedHistogramBucketExemplarReservoir,
    ExemplarReservoirBuilder,
    SimpleFixedSizeExemplarReservoir,
)
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.trace import TracerProvider


# Create a custom reservoir factory with specified parameters
def custom_reservoir_factory(
    aggregationType: Type[_Aggregation],
) -> ExemplarReservoirBuilder:
    if issubclass(aggregationType, _ExplicitBucketHistogramAggregation):
        return AlignedHistogramBucketExemplarReservoir
    else:
        # Custom reservoir must accept `**kwargs` that may set the `size` for
        # _ExponentialBucketHistogramAggregation or the `boundaries` for
        # _ExplicitBucketHistogramAggregation
        return lambda **kwargs: SimpleFixedSizeExemplarReservoir(
            size=10,
            **{k: v for k, v in kwargs.items() if k != "size"},
        )


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

# Create a trace and span as the default exemplar filter `TraceBasedExemplarFilter`
# will only store exemplar if a context exists
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("foo"):
    while 1:
        my_counter.add(random.randint(1, 10))
        time.sleep(random.random())
