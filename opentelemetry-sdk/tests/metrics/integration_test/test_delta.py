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

from io import StringIO
from itertools import count
from json import loads
from time import sleep
from unittest import TestCase

from opentelemetry.metrics import (
    Observation,
    get_meter_provider,
    set_meter_provider,
)
from opentelemetry.sdk.metrics import MeterProvider, ObservableCounter
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.metrics.view import SumAggregation
from opentelemetry.test.globals_test import reset_metrics_globals

network_bytes_generator = count(start=8, step=8)

counter = 0


def observable_counter_callback(callback_options):

    global counter

    counter += 1

    yield Observation(next(network_bytes_generator))


class TestDelta(TestCase):
    def test_observable_counter_delta(self):
        def setUp(self):
            reset_metrics_globals()

        def tearDown(self):
            reset_metrics_globals()

        output = StringIO()

        aggregation = SumAggregation()

        exporter = ConsoleMetricExporter(
            out=output,
            preferred_aggregation={ObservableCounter: aggregation},
            preferred_temporality={
                ObservableCounter: AggregationTemporality.DELTA
            },
        )

        reader = PeriodicExportingMetricReader(
            exporter, export_interval_millis=100
        )

        provider = MeterProvider(metric_readers=[reader])
        set_meter_provider(provider)

        meter = get_meter_provider().get_meter(
            "preferred-aggregation", "0.1.2"
        )

        meter.create_observable_counter(
            "observable_counter", [observable_counter_callback]
        )

        sleep(1)

        provider.shutdown()

        output.seek(0)

        joined_output = "".join(output.readlines())

        stack = []

        sections = []

        previous_index = 0

        for current_index, character in enumerate(joined_output):

            if character == "{":

                if not stack:
                    previous_index = current_index

                stack.append(character)

            elif character == "}":
                stack.pop()

                if not stack:

                    sections.append(
                        joined_output[
                            previous_index : current_index + 1
                        ].strip()
                    )

        joined_output = f"[{','.join(sections)}]"

        result = loads(joined_output)

        previous_time_unix_nano = result[0]["resource_metrics"][0][
            "scope_metrics"
        ][0]["metrics"][0]["data"]["data_points"][0]["time_unix_nano"]

        for element in result[1:]:

            metric_data = element["resource_metrics"][0]["scope_metrics"][0][
                "metrics"
            ][0]["data"]["data_points"][0]

            self.assertEqual(
                previous_time_unix_nano, metric_data["start_time_unix_nano"]
            )
            previous_time_unix_nano = metric_data["time_unix_nano"]
            self.assertEqual(metric_data["value"], 8)
