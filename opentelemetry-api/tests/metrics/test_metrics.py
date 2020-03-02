# Copyright 2020, OpenTelemetry Authors
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

from opentelemetry import metrics


# pylint: disable=no-self-use
class TestMetrics(unittest.TestCase):
    def test_default(self):
        default = metrics.DefaultMetric()
        default_ls = metrics.DefaultLabelSet()
        handle = default.get_handle(default_ls)
        self.assertIsInstance(handle, metrics.DefaultMetricHandle)

    def test_counter(self):
        counter = metrics.Counter()
        label_set = metrics.LabelSet()
        handle = counter.get_handle(label_set)
        self.assertIsInstance(handle, metrics.CounterHandle)

    def test_counter_add(self):
        counter = metrics.Counter()
        label_set = metrics.LabelSet()
        counter.add(1, label_set)

    def test_measure(self):
        measure = metrics.Measure()
        label_set = metrics.LabelSet()
        handle = measure.get_handle(label_set)
        self.assertIsInstance(handle, metrics.MeasureHandle)

    def test_measure_record(self):
        measure = metrics.Measure()
        label_set = metrics.LabelSet()
        measure.record(1, label_set)

    def test_default_handle(self):
        metrics.DefaultMetricHandle()

    def test_counter_handle(self):
        handle = metrics.CounterHandle()
        handle.add(1)

    def test_measure_handle(self):
        handle = metrics.MeasureHandle()
        handle.record(1)
