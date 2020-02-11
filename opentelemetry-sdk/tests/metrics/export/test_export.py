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

from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricsExporter,
    MetricRecord,
)
from opentelemetry.sdk.metrics.export.aggregate import CounterAggregator
from opentelemetry.sdk.metrics.export.batcher import UngroupedBatcher
from opentelemetry.sdk.metrics.export.controller import PushController


# pylint: disable=protected-access
class TestConsoleMetricsExporter(unittest.TestCase):
    # pylint: disable=no-self-use
    def test_export(self):
        meter = metrics.Meter()
        exporter = ConsoleMetricsExporter()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        kvp = {"environment": "staging"}
        label_set = meter.get_label_set(kvp)
        aggregator = CounterAggregator()
        record = MetricRecord(aggregator, label_set, metric)
        result = '{}(data="{}", label_set="{}", value={})'.format(
            ConsoleMetricsExporter.__name__,
            metric,
            label_set.labels,
            aggregator.checkpoint,
        )
        with mock.patch("sys.stdout") as mock_stdout:
            exporter.export([record])
            mock_stdout.write.assert_any_call(result)


class TestBatcher(unittest.TestCase):
    def test_aggregator_for_counter(self):
        batcher = UngroupedBatcher(True)
        self.assertTrue(
            isinstance(
                batcher.aggregator_for(metrics.Counter), CounterAggregator
            )
        )

    # TODO: Add other aggregator tests

    def test_checkpoint_set(self):
        meter = metrics.Meter()
        batcher = UngroupedBatcher(True)
        aggregator = CounterAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        aggregator.update(1.0)
        label_set = metrics.LabelSet()
        _batch_map = {}
        _batch_map[(metric, label_set)] = aggregator
        batcher._batch_map = _batch_map
        records = batcher.checkpoint_set()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].metric, metric)
        self.assertEqual(records[0].label_set, label_set)
        self.assertEqual(records[0].aggregator, aggregator)

    def test_checkpoint_set_empty(self):
        batcher = UngroupedBatcher(True)
        records = batcher.checkpoint_set()
        self.assertEqual(len(records), 0)

    def test_finished_collection_stateless(self):
        meter = metrics.Meter()
        batcher = UngroupedBatcher(False)
        aggregator = CounterAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        aggregator.update(1.0)
        label_set = metrics.LabelSet()
        _batch_map = {}
        _batch_map[(metric, label_set)] = aggregator
        batcher._batch_map = _batch_map
        batcher.finished_collection()
        self.assertEqual(len(batcher._batch_map), 0)

    def test_finished_collection_stateful(self):
        meter = metrics.Meter()
        batcher = UngroupedBatcher(True)
        aggregator = CounterAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        aggregator.update(1.0)
        label_set = metrics.LabelSet()
        _batch_map = {}
        _batch_map[(metric, label_set)] = aggregator
        batcher._batch_map = _batch_map
        batcher.finished_collection()
        self.assertEqual(len(batcher._batch_map), 1)

    # TODO: Abstract the logic once other batchers implemented
    def test_ungrouped_batcher_process_exists(self):
        meter = metrics.Meter()
        batcher = UngroupedBatcher(True)
        aggregator = CounterAggregator()
        aggregator2 = CounterAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        label_set = metrics.LabelSet()
        _batch_map = {}
        _batch_map[(metric, label_set)] = aggregator
        aggregator2.update(1.0)
        batcher._batch_map = _batch_map
        record = metrics.Record(metric, label_set, aggregator2)
        batcher.process(record)
        self.assertEqual(len(batcher._batch_map), 1)
        self.assertIsNotNone(batcher._batch_map.get((metric, label_set)))
        self.assertEqual(
            batcher._batch_map.get((metric, label_set)).current, 0
        )
        self.assertEqual(
            batcher._batch_map.get((metric, label_set)).checkpoint, 1.0
        )

    def test_ungrouped_batcher_process_not_exists(self):
        meter = metrics.Meter()
        batcher = UngroupedBatcher(True)
        aggregator = CounterAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        label_set = metrics.LabelSet()
        _batch_map = {}
        aggregator.update(1.0)
        batcher._batch_map = _batch_map
        record = metrics.Record(metric, label_set, aggregator)
        batcher.process(record)
        self.assertEqual(len(batcher._batch_map), 1)
        self.assertIsNotNone(batcher._batch_map.get((metric, label_set)))
        self.assertEqual(
            batcher._batch_map.get((metric, label_set)).current, 0
        )
        self.assertEqual(
            batcher._batch_map.get((metric, label_set)).checkpoint, 1.0
        )

    def test_ungrouped_batcher_process_not_stateful(self):
        meter = metrics.Meter()
        batcher = UngroupedBatcher(True)
        aggregator = CounterAggregator()
        metric = metrics.Counter(
            "available memory",
            "available memory",
            "bytes",
            int,
            meter,
            ("environment",),
        )
        label_set = metrics.LabelSet()
        _batch_map = {}
        aggregator.update(1.0)
        batcher._batch_map = _batch_map
        record = metrics.Record(metric, label_set, aggregator)
        batcher.process(record)
        self.assertEqual(len(batcher._batch_map), 1)
        self.assertIsNotNone(batcher._batch_map.get((metric, label_set)))
        self.assertEqual(
            batcher._batch_map.get((metric, label_set)).current, 0
        )
        self.assertEqual(
            batcher._batch_map.get((metric, label_set)).checkpoint, 1.0
        )


class TestAggregator(unittest.TestCase):
    # TODO: test other aggregators once implemented
    def test_counter_update(self):
        counter = CounterAggregator()
        counter.update(1.0)
        counter.update(2.0)
        self.assertEqual(counter.current, 3.0)

    def test_counter_checkpoint(self):
        counter = CounterAggregator()
        counter.update(2.0)
        counter.take_checkpoint()
        self.assertEqual(counter.current, 0)
        self.assertEqual(counter.checkpoint, 2.0)

    def test_counter_merge(self):
        counter = CounterAggregator()
        counter2 = CounterAggregator()
        counter.checkpoint = 1.0
        counter2.checkpoint = 3.0
        counter.merge(counter2)
        self.assertEqual(counter.checkpoint, 4.0)


class TestController(unittest.TestCase):
    def test_push_controller(self):
        meter = mock.Mock()
        exporter = mock.Mock()
        controller = PushController(meter, exporter, 5.0)
        meter.collect.assert_not_called()
        exporter.export.assert_not_called()
        controller.shutdown()
        self.assertTrue(controller.finished.isSet())
        exporter.shutdown.assert_any_call()
