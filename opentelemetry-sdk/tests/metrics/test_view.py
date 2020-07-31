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
from opentelemetry.sdk.metrics import Counter, view
from opentelemetry.sdk.metrics.export import aggregate
from opentelemetry.sdk.metrics.export.aggregate import (
    MinMaxSumCountAggregator,
    SumAggregator,
)
from opentelemetry.sdk.metrics.export.controller import PushController
from opentelemetry.sdk.metrics.export.in_memory_metrics_exporter import (
    InMemoryMetricsExporter,
)
from opentelemetry.sdk.metrics.view import View, ViewConfig


class TestUtil(unittest.TestCase):
    @mock.patch("opentelemetry.sdk.metrics.view.logger")
    def test_default_aggregator(self, logger_mock):
        meter = metrics.MeterProvider().get_meter(__name__)
        counter = metrics.Counter("", "", "1", int, meter)
        self.assertEqual(
            view.get_default_aggregator(counter), aggregate.SumAggregator,
        )
        ud_counter = metrics.UpDownCounter("", "", "1", int, meter)
        self.assertEqual(
            view.get_default_aggregator(ud_counter), aggregate.SumAggregator,
        )
        observer = metrics.SumObserver(lambda: None, "", "", "1", int)
        self.assertEqual(
            view.get_default_aggregator(observer),
            aggregate.LastValueAggregator,
        )
        ud_observer = metrics.SumObserver(lambda: None, "", "", "1", int)
        self.assertEqual(
            view.get_default_aggregator(ud_observer),
            aggregate.LastValueAggregator,
        )
        recorder = metrics.ValueRecorder("", "", "1", int, meter)
        self.assertEqual(
            view.get_default_aggregator(recorder),
            aggregate.MinMaxSumCountAggregator,
        )
        v_observer = metrics.ValueObserver(lambda: None, "", "", "1", int)
        self.assertEqual(
            view.get_default_aggregator(v_observer),
            aggregate.ValueObserverAggregator,
        )
        self.assertEqual(
            view.get_default_aggregator(DummyMetric()),
            aggregate.SumAggregator,
        )
        self.assertEqual(logger_mock.warning.call_count, 1)


class TestStateless(unittest.TestCase):
    def setUp(self):
        self.meter = metrics.MeterProvider(stateful=False).get_meter(__name__)
        self.exporter = InMemoryMetricsExporter()
        self.controller = PushController(self.meter, self.exporter, 30)

    def tearDown(self):
        self.controller.shutdown()

    def test_label_keys(self):
        test_counter = self.meter.create_metric(
            name="test_counter",
            description="description",
            unit="By",
            value_type=int,
            metric_type=Counter,
        )
        counter_view = View(
            test_counter,
            SumAggregator,
            label_keys=["environment"],
            view_config=ViewConfig.LABEL_KEYS,
        )

        self.meter.register_view(counter_view)
        test_counter.add(6, {"environment": "production", "customer_id": 123})
        test_counter.add(5, {"environment": "production", "customer_id": 247})

        self.controller.tick()

        metric_data = self.exporter.get_exported_metrics()
        self.assertEqual(len(metric_data), 1)
        self.assertEqual(
            metric_data[0].labels, (("environment", "production"),)
        )
        self.assertEqual(metric_data[0].aggregator.checkpoint, 11)

    def test_ungrouped(self):
        test_counter = self.meter.create_metric(
            name="test_counter",
            description="description",
            unit="By",
            value_type=int,
            metric_type=Counter,
        )
        counter_view = View(
            test_counter,
            SumAggregator,
            label_keys=["environment"],
            view_config=ViewConfig.UNGROUPED,
        )

        self.meter.register_view(counter_view)
        test_counter.add(6, {"environment": "production", "customer_id": 123})
        test_counter.add(5, {"environment": "production", "customer_id": 247})

        self.controller.tick()

        metric_data = self.exporter.get_exported_metrics()
        self.assertEqual(len(metric_data), 2)
        self.assertEqual(
            metric_data[0].labels,
            (("customer_id", 123), ("environment", "production")),
        )
        self.assertEqual(
            metric_data[1].labels,
            (("customer_id", 247), ("environment", "production")),
        )
        self.assertEqual(metric_data[0].aggregator.checkpoint, 6)
        self.assertEqual(metric_data[1].aggregator.checkpoint, 5)

    def test_multiple_views(self):
        test_counter = self.meter.create_metric(
            name="test_counter",
            description="description",
            unit="By",
            value_type=int,
            metric_type=Counter,
        )

        counter_view = View(
            test_counter,
            SumAggregator,
            label_keys=["environment"],
            view_config=ViewConfig.UNGROUPED,
        )

        mmsc_view = View(
            test_counter,
            MinMaxSumCountAggregator,
            label_keys=["environment"],
            view_config=ViewConfig.LABEL_KEYS,
        )

        self.meter.register_view(counter_view)
        self.meter.register_view(mmsc_view)
        test_counter.add(6, {"environment": "production", "customer_id": 123})
        test_counter.add(5, {"environment": "production", "customer_id": 247})

        self.controller.tick()

        metric_data = self.exporter.get_exported_metrics()
        self.assertEqual(len(metric_data), 3)
        self.assertEqual(
            metric_data[0].labels, (("environment", "production"),)
        )
        self.assertEqual(
            metric_data[1].labels,
            (("customer_id", 123), ("environment", "production")),
        )
        self.assertEqual(
            metric_data[2].labels,
            (("customer_id", 247), ("environment", "production")),
        )

        self.assertEqual(metric_data[0].aggregator.checkpoint.sum, 11)
        self.assertEqual(metric_data[1].aggregator.checkpoint, 6)
        self.assertEqual(metric_data[2].aggregator.checkpoint, 5)


class DummyMetric(metrics.Metric):
    # pylint: disable=W0231
    def __init__(self):
        pass
