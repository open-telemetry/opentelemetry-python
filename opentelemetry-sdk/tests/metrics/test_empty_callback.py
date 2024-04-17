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
# type: ignore

from unittest import TestCase

from opentelemetry.metrics import CallbackOptions
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.export import InMemoryMetricReader


class TestEptyCallback(TestCase):
    def test_empty_callback(self):
        def empty_callback(
            options: CallbackOptions,
        ) -> None:
            yield None
            yield None
            yield None

        in_memory_metric_reader = InMemoryMetricReader()
        (
            MeterProvider(metric_readers=[in_memory_metric_reader])
            .get_meter("name")
            .create_observable_counter(
                "observable_counter",
                callbacks=[empty_callback],
            )
        )
        self.assertIsNone(in_memory_metric_reader.get_metrics_data())
