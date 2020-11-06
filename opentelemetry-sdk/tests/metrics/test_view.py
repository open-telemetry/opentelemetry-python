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
from math import inf
from unittest import mock

from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics import view
from opentelemetry.sdk.metrics.export import aggregate
from opentelemetry.sdk.metrics.export.aggregate import (
    HistogramAggregator,
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
            view.get_default_aggregator(counter), aggregate.SumAggregator
        )
        ud_counter = metrics.UpDownCounter("", "", "1", int, meter)
        self.assertEqual(
            view.get_default_aggregator(ud_counter), aggregate.SumAggregator
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
            view.get_default_aggregator(DummyMetric()), aggregate.SumAggregator
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
        test_counter = self.meter.create_counter(
            name="test_counter",
            description="description",
            unit="By",
            value_type=int,
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
        test_counter = self.meter.create_counter(
            name="test_counter",
            description="description",
            unit="By",
            value_type=int,
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
        data_set = set()
        for data in metric_data:
            data_set.add((data.labels, data.aggregator.checkpoint))
        self.assertEqual(len(metric_data), 2)
        label1 = (("customer_id", 123), ("environment", "production"))
        label2 = (("customer_id", 247), ("environment", "production"))
        self.assertTrue((label1, 6) in data_set)
        self.assertTrue((label2, 5) in data_set)

    def test_multiple_views(self):
        test_counter = self.meter.create_counter(
            name="test_counter",
            description="description",
            unit="By",
            value_type=int,
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
        sum_set = set()
        mmsc_set = set()
        for data in metric_data:
            if isinstance(data.aggregator, SumAggregator):
                tup = (data.labels, data.aggregator.checkpoint)
                sum_set.add(tup)
            elif isinstance(data.aggregator, MinMaxSumCountAggregator):
                mmsc_set.add(data)
                self.assertEqual(data.labels, (("environment", "production"),))
                self.assertEqual(data.aggregator.checkpoint.sum, 11)
        # we have to assert this way because order is unknown
        self.assertEqual(len(sum_set), 2)
        self.assertEqual(len(mmsc_set), 1)
        label1 = (("customer_id", 123), ("environment", "production"))
        label2 = (("customer_id", 247), ("environment", "production"))
        self.assertTrue((label1, 6) in sum_set)
        self.assertTrue((label2, 5) in sum_set)


class TestHistogramView(unittest.TestCase):
    def test_histogram_stateful(self):
        meter = metrics.MeterProvider(stateful=True).get_meter(__name__)
        exporter = InMemoryMetricsExporter()
        controller = PushController(meter, exporter, 30)

        requests_size = meter.create_valuerecorder(
            name="requests_size",
            description="size of requests",
            unit="1",
            value_type=int,
        )

        size_view = View(
            requests_size,
            HistogramAggregator,
            aggregator_config={"bounds": [20, 40, 60, 80, 100]},
            label_keys=["environment"],
            view_config=ViewConfig.LABEL_KEYS,
        )

        meter.register_view(size_view)

        # Since this is using the HistogramAggregator, the bucket counts will be reflected
        # with each record
        requests_size.record(25, {"environment": "staging", "test": "value"})
        requests_size.record(1, {"environment": "staging", "test": "value2"})
        requests_size.record(200, {"environment": "staging", "test": "value3"})

        controller.tick()

        metrics_list = exporter.get_exported_metrics()
        self.assertEqual(len(metrics_list), 1)
        checkpoint = metrics_list[0].aggregator.checkpoint
        self.assertEqual(
            tuple(checkpoint.items()),
            ((20, 1), (40, 1), (60, 0), (80, 0), (100, 0), (inf, 1)),
        )
        exporter.clear()

        requests_size.record(25, {"environment": "staging", "test": "value"})
        requests_size.record(1, {"environment": "staging", "test": "value2"})
        requests_size.record(200, {"environment": "staging", "test": "value3"})

        controller.tick()

        metrics_list = exporter.get_exported_metrics()
        self.assertEqual(len(metrics_list), 1)
        checkpoint = metrics_list[0].aggregator.checkpoint
        self.assertEqual(
            tuple(checkpoint.items()),
            ((20, 2), (40, 2), (60, 0), (80, 0), (100, 0), (inf, 2)),
        )

    def test_histogram_stateless(self):
        # Use the meter type provided by the SDK package
        meter = metrics.MeterProvider(stateful=False).get_meter(__name__)
        exporter = InMemoryMetricsExporter()
        controller = PushController(meter, exporter, 30)

        requests_size = meter.create_valuerecorder(
            name="requests_size",
            description="size of requests",
            unit="1",
            value_type=int,
        )

        size_view = View(
            requests_size,
            HistogramAggregator,
            aggregator_config={"bounds": [20, 40, 60, 80, 100]},
            label_keys=["environment"],
            view_config=ViewConfig.LABEL_KEYS,
        )

        meter.register_view(size_view)

        # Since this is using the HistogramAggregator, the bucket counts will be reflected
        # with each record
        requests_size.record(25, {"environment": "staging", "test": "value"})
        requests_size.record(1, {"environment": "staging", "test": "value2"})
        requests_size.record(200, {"environment": "staging", "test": "value3"})

        controller.tick()

        metrics_list = exporter.get_exported_metrics()
        self.assertEqual(len(metrics_list), 1)
        checkpoint = metrics_list[0].aggregator.checkpoint
        self.assertEqual(
            tuple(checkpoint.items()),
            ((20, 1), (40, 1), (60, 0), (80, 0), (100, 0), (inf, 1)),
        )
        exporter.clear()

        requests_size.record(25, {"environment": "staging", "test": "value"})
        requests_size.record(1, {"environment": "staging", "test": "value2"})
        requests_size.record(200, {"environment": "staging", "test": "value3"})

        controller.tick()

        metrics_list = exporter.get_exported_metrics()
        self.assertEqual(len(metrics_list), 1)
        checkpoint = metrics_list[0].aggregator.checkpoint
        self.assertEqual(
            tuple(checkpoint.items()),
            ((20, 1), (40, 1), (60, 0), (80, 0), (100, 0), (inf, 1)),
        )


class DummyMetric(metrics.Metric):
    # pylint: disable=W0231
    def __init__(self):
        pass
