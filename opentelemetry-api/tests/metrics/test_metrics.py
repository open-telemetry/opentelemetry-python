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
    def test_default_counter(self):
        counter = metrics.DefaultCounter()
        bound_counter = counter.bind({})
        self.assertIsInstance(bound_counter, metrics.DefaultBoundCounter)

    def test_default_counter_add(self):
        counter = metrics.DefaultCounter()
        counter.add(1, {})

    def test_default_updowncounter(self):
        counter = metrics.DefaultUpDownCounter()
        bound_counter = counter.bind({})
        self.assertIsInstance(bound_counter, metrics.DefaultBoundUpDownCounter)

    def test_default_updowncounter_add(self):
        counter = metrics.DefaultUpDownCounter()
        counter.add(1, {})
        counter.add(-1, {})

    def test_default_valuerecorder(self):
        valuerecorder = metrics.DefaultValueRecorder()
        bound_valuerecorder = valuerecorder.bind({})
        self.assertIsInstance(
            bound_valuerecorder, metrics.DefaultBoundValueRecorder
        )

    def test_default_valuerecorder_record(self):
        valuerecorder = metrics.DefaultValueRecorder()
        valuerecorder.record(1, {})

    def test_default_bound_counter(self):
        bound_counter = metrics.DefaultBoundCounter()
        bound_counter.add(1)

    def test_default_bound_updowncounter(self):
        bound_counter = metrics.DefaultBoundUpDownCounter()
        bound_counter.add(1)

    def test_default_bound_valuerecorder(self):
        bound_valuerecorder = metrics.DefaultBoundValueRecorder()
        bound_valuerecorder.record(1)

    def test_default_sum_observer(self):
        observer = metrics.DefaultSumObserver()
        observer.observe(1, {})

    def test_default_updown_sum_observer(self):
        observer = metrics.DefaultUpDownSumObserver()
        observer.observe(1, {})

    def test_default_value_observer(self):
        observer = metrics.DefaultValueObserver()
        observer.observe(1, {})
