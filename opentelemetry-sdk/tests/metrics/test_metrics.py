# Copyright 2019, OpenTelemetry Authors
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

import unittest
from unittest import mock

from opentelemetry import metrics as metrics_api
from opentelemetry.sdk import metrics


class TestMeter(unittest.TestCase):
    def test_extends_api(self):
        meter = metrics.Meter()
        self.assertIsInstance(meter, metrics_api.Meter)

    def test_record_batch(self):
        meter = metrics.Meter()
        label_keys = ["key1"]
        label_values = ("value1")
        float_counter = metrics.FloatCounter(
            "name",
            "desc",
            "unit",
            label_keys,
        )
        record_tuples = [(float_counter, 1.0)]
        meter.record_batch(label_values, record_tuples)
        self.assertEqual(float_counter.get_handle(label_values).data, 1.0)

    def test_record_batch_exists(self):
        meter = metrics.Meter()
        label_keys = ["key1"]
        label_values = ("value1")
        float_counter = metrics.FloatCounter(
            "name",
            "desc",
            "unit",
            label_keys
        )
        handle = float_counter.get_handle(label_values)
        handle.update(1.0)
        record_tuples = [(float_counter, 1.0)]
        meter.record_batch(label_values, record_tuples)
        self.assertEqual(float_counter.get_handle(label_values), handle)
        self.assertEqual(handle.data, 2.0)
