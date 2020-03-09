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
        bound_metric = default.bind(default_ls)
        self.assertIsInstance(bound_metric, metrics.DefaultBoundMetric)

    def test_counter(self):
        counter = metrics.Counter()
        label_set = metrics.LabelSet()
        bound_metric = counter.bind(label_set)
        self.assertIsInstance(bound_metric, metrics.BoundCounter)

    def test_counter_add(self):
        counter = metrics.Counter()
        label_set = metrics.LabelSet()
        counter.add(1, label_set)

    def test_measure(self):
        measure = metrics.Measure()
        label_set = metrics.LabelSet()
        bound_metric = measure.bind(label_set)
        self.assertIsInstance(bound_metric, metrics.BoundMeasure)

    def test_measure_record(self):
        measure = metrics.Measure()
        label_set = metrics.LabelSet()
        measure.record(1, label_set)

    def test_default_bound_metric(self):
        metrics.DefaultBoundMetric()

    def test_bound_counter(self):
        bound_metric = metrics.BoundCounter()
        bound_metric.add(1)

    def test_bound_measure(self):
        bound_metric = metrics.BoundMeasure()
        bound_metric.record(1)
