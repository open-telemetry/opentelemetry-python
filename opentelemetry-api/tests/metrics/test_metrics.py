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

import unittest

from opentelemetry import metrics


# pylint: disable=no-self-use
class TestMetrics(unittest.TestCase):
    def test_default(self):
        default = metrics.DefaultMetric()
        bound_metric_instr = default.bind({})
        self.assertIsInstance(
            bound_metric_instr, metrics.DefaultBoundInstrument
        )

    def test_counter(self):
        counter = metrics.Counter()
        bound_counter = counter.bind({})
        self.assertIsInstance(bound_counter, metrics.BoundCounter)

    def test_counter_add(self):
        counter = metrics.Counter()
        counter.add(1, {})

    def test_updowncounter(self):
        counter = metrics.UpDownCounter()
        bound_counter = counter.bind({})
        self.assertIsInstance(bound_counter, metrics.BoundUpDownCounter)

    def test_updowncounter_add(self):
        counter = metrics.Counter()
        counter.add(1, {})
        counter.add(-1, {})

    def test_valuerecorder(self):
        valuerecorder = metrics.ValueRecorder()
        bound_valuerecorder = valuerecorder.bind({})
        self.assertIsInstance(bound_valuerecorder, metrics.BoundValueRecorder)

    def test_valuerecorder_record(self):
        valuerecorder = metrics.ValueRecorder()
        valuerecorder.record(1, {})

    def test_default_bound_metric(self):
        bound_instrument = metrics.DefaultBoundInstrument()
        bound_instrument.release()

    def test_bound_counter(self):
        bound_counter = metrics.BoundCounter()
        bound_counter.add(1)

    def test_bound_valuerecorder(self):
        bound_valuerecorder = metrics.BoundValueRecorder()
        bound_valuerecorder.record(1)

    def test_default_observer(self):
        observer = metrics.DefaultObserver()
        observer.observe(1, {})

    def test_sum_observer(self):
        observer = metrics.SumObserver()
        observer.observe(1, {})

    def test_updown_sum_observer(self):
        observer = metrics.UpDownSumObserver()
        observer.observe(1, {})

    def test_value_observer(self):
        observer = metrics.ValueObserver()
        observer.observe(1, {})
