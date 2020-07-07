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
from unittest import mock

from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics import view
from opentelemetry.sdk.metrics.export import aggregate


class TestUtil(unittest.TestCase):
    @mock.patch("opentelemetry.sdk.metrics.view.logger")
    def test_default_aggregator(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        counter = metrics.Counter("", "", "1", int, meter)
        self.assertTrue(
            isinstance(
                view.get_default_aggregator(counter), aggregate.SumAggregator
            )
        )
        ud_counter = metrics.UpDownCounter("", "", "1", int, meter)
        self.assertTrue(
            isinstance(
                view.get_default_aggregator(ud_counter),
                aggregate.SumAggregator,
            )
        )
        observer = metrics.SumObserver(lambda: None, "", "", "1", int)
        self.assertTrue(
            isinstance(
                view.get_default_aggregator(observer),
                aggregate.LastValueAggregator,
            )
        )
        ud_observer = metrics.SumObserver(lambda: None, "", "", "1", int)
        self.assertTrue(
            isinstance(
                view.get_default_aggregator(ud_observer),
                aggregate.LastValueAggregator,
            )
        )
        recorder = metrics.ValueRecorder("", "", "1", int, meter)
        self.assertTrue(
            isinstance(
                view.get_default_aggregator(recorder),
                aggregate.MinMaxSumCountAggregator,
            )
        )
        v_observer = metrics.ValueObserver(lambda: None, "", "", "1", int)
        self.assertTrue(
            isinstance(
                view.get_default_aggregator(v_observer),
                aggregate.ValueObserverAggregator,
            )
        )
        self.assertTrue(
            isinstance(
                view.get_default_aggregator(DummyMetric()),
                aggregate.SumAggregator,
            )
        )
        self.assertEqual(logger_mock.warning.call_count, 1)


class DummyMetric(metrics.Metric):
    # pylint: disable=W0231
    def __init__(self):
        pass
